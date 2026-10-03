// Autonomous completed-frame consumer. All addresses are logical PSRAM words.
// Capture map is shared; IDs/dictionaries are banked. next-use at 420000,
// six palette events per row at 430000. Output sinks acknowledge COMMIT.
// Palette output is semantic data, not yet SNES HDMA table encoding.
module frame_pipeline_ring3(
 input wire clk,reset,start,lcd_on,pixel_valid,input wire[14:0]pixel_rgb,
 output wire armed,output wire[6:0]fifo_level,
 output wire error,output wire[3:0]error_code,
 output wire req_valid,req_write,output wire[22:0]req_addr,
 output wire[15:0]req_data,input wire req_ready,rsp_valid,input wire[15:0]rsp_data,
 output wire word_valid,input wire word_ready,
 output wire[14:0]word_addr,output wire[15:0]word_data,
 output wire palette_valid,input wire palette_ready,
 output wire palette_initial,output wire[7:0]palette_after_row,
 output wire[5:0]palette_slot,output wire[14:0]palette_rgb,
 output reg frame_done,output wire[1:0]processing_bank,output wire[4:0]debug_state,output wire[23:0]fault_context
);

 localparam IDLE=0,BSTART=3,BWAIT=4,INIT=5,PSTART=6,PWAIT=7,
 DREQ=10,DWAIT=11,PALOUT=12,VSTART=13,ROW=14,IREQ=17,IWAIT=18,
 LOW=19,HIGH=20,FINISH=21,FAILED=22,HREQ=23,HWAIT=24;
 reg[4:0]state;assign debug_state=state;
 reg[1:0]bank_q;reg[9:0]count_q;reg[5:0]slot_q;reg[8:0]id_q;
 reg[7:0]row_q,x_q;reg initial_palette;
 reg[15:0]ids_q,high_bits;reg[14:0]rgb_q;reg[2:0]release_bank;
 wire[2:0]banks;wire[9:0]count0,count1,count2;wire[23:0]capture_fault;
 wire ce;wire[2:0]cc;reg[3:0]stored_error_code;
 assign error_code=ce?{1'b0,cc}:stored_error_code;
 wire cv,cw;wire[22:0]ca;wire[15:0]cd;
 wire[4:0]accepted,responded;wire[15:0]response;
 capture_ring3_lcd capture(clk,reset,start,lcd_on,pixel_valid,pixel_rgb,release_bank,
 banks,count0,count1,count2,armed,ce,cc,cv,cw,accepted[0],ca,cd,responded[0],response,fifo_level,5'd0,capture_fault);
 wire br,bw,bd,be,bb;wire[14:0]bra;wire[16:0]bwa;wire[15:0]bwd;
 wire local_reset=reset||state==IDLE;
 next_use_builder builder(clk,local_reset,state==BSTART,count_q,
 br,accepted[1],bra,responded[1],response,bw,responded[2],bwa,bwd,bd,be,bb);
 reg palette_fault_selected;wire[15:0]palette_fault;
 wire pr,pu,pd,pe,pb,prow;wire[16:0]pra;wire[7:0]pur;wire[8:0]pui;wire[5:0]pus;
 reg planner_lane,planner_cache_valid;reg[15:0]planner_cache_addr,planner_cache_data;
 wire planner_cache_hit=pr&&planner_cache_valid&&pra[16:1]==planner_cache_addr;
 wire planner_accept=accepted[3]||planner_cache_hit;
 wire planner_response=responded[3]||planner_cache_hit;
 wire[15:0]planner_word=planner_cache_hit?planner_cache_data:response;
 always @(posedge clk)begin
  if(local_reset)begin planner_cache_valid<=0;planner_cache_addr<=0;planner_cache_data<=0;end
  else begin
   if(accepted[3])begin planner_cache_addr<=pra[16:1];planner_cache_valid<=0;end
   if(responded[3])begin planner_cache_data<=response;planner_cache_valid<=1;end
  end
 end
 wire[8:0]evicted_id;
 wire[8:0]init_id={4'b0,slot_q}<count_q?{3'b0,slot_q}:9'd0;
 palette_planner planner(clk,local_reset,state==PSTART,count_q,state==INIT,
 slot_q,init_id,pr,planner_accept,pra,planner_response,(planner_cache_hit?pra[0]:planner_lane)?planner_word[15:8]:planner_word[7:0],
 pu,state==PALOUT&&palette_ready&&!initial_palette,pur,pus,pui,pd,pe,pb,palette_fault,prow,state==PWAIT&&prow,evicted_id);
 wire vpready,vd,ve,vb;wire[7:0]vy,vx;
 wire vpal=state==INIT||(state==PALOUT&&palette_ready&&!initial_palette);
 indexed_sixplane converter(clk,local_reset,state==VSTART,vpal,slot_q,
 state==INIT?init_id:id_q,state==LOW||state==HIGH,
 state==LOW?{high_bits[x_q[3:0]],ids_q[7:0]}:{high_bits[x_q[3:0]+4'd1],ids_q[15:8]},vpready,vy,vx,
 word_valid,word_ready,word_addr,word_data,vd,ve,vb,evicted_id,state==INIT,count_q);
 wire own_req=state==DREQ||state==IREQ||state==HREQ;
 wire[22:0]frame_base=23'h400000+{5'b0,bank_q,16'b0};
 wire[22:0]own_addr=state==DREQ ? frame_base+23'he000+id_q :
 state==HREQ ? frame_base+23'hb000+row_q*23'd10+{19'b0,x_q[7:4]} : frame_base+23'h8000+row_q*23'd80+{16'b0,x_q[7:1]};
 video_router router(clk,reset,fifo_level>=7'd16,{own_req,(pr&&!planner_cache_hit),bw,br,cv},
 {1'b0,1'b0,1'b1,1'b0,cw},
 {own_addr,(23'h430000+{7'b0,pra[16:1]}),(23'h430000+{7'b0,bwa[16:1]}),
 (frame_base+23'h8000+{8'b0,bra}),ca},
 {16'd0,16'd0,bwd,16'd0,cd},accepted,responded,response,
 req_valid,req_write,req_addr,req_data,req_ready,rsp_valid,rsp_data);
 assign palette_valid=state==PALOUT;
 assign palette_initial=initial_palette;assign palette_after_row=row_q-1'b1;
 assign palette_slot=slot_q;assign palette_rgb=rgb_q;assign processing_bank=bank_q;
 assign fault_context=palette_fault_selected ? {8'b0,palette_fault} : capture_fault;
 always @(posedge clk)begin
  if(reset)palette_fault_selected<=0;
  else if(state!=FAILED&&pe&&!ce&&!be)palette_fault_selected<=1;
 end
 assign error=ce||state==FAILED;
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;bank_q<=0;count_q<=0;slot_q<=0;id_q<=0;row_q<=0;x_q<=0;
   initial_palette<=1;ids_q<=0;high_bits<=0;rgb_q<=0;release_bank<=0;frame_done<=0;
   stored_error_code<=0;planner_lane<=0;
  end else begin
   release_bank<=0;frame_done<=0;if(planner_accept)planner_lane<=pra[0];
   case(state)
    IDLE:if(banks[bank_q])begin
     count_q<=bank_q==2?count2:bank_q==1?count1:count0;row_q<=0;x_q<=0;state<=BSTART;
    end
    BSTART:state<=BWAIT;
    BWAIT:if(bd)begin slot_q<=0;state<=INIT;end
    INIT:if(slot_q==63)begin slot_q<=0;id_q<=0;initial_palette<=1;state<=DREQ;end else slot_q<=slot_q+1'b1;
    DREQ:if(accepted[4])state<=DWAIT;
    DWAIT:if(responded[4])begin rgb_q<=response[14:0];state<=PALOUT;end
    PALOUT:if(palette_ready)begin
     if(initial_palette)begin
      if(slot_q==63)begin initial_palette<=0;state<=VSTART;end
      else begin slot_q<=slot_q+1'b1;id_q<=({4'b0,slot_q}+10'd1<count_q)?{3'b0,slot_q}+9'd1:9'd0;state<=DREQ;end
     end else state<=PWAIT;
    end
    VSTART:state<=PSTART;
    PSTART:state<=PWAIT;
    PWAIT:if(pu)begin
     if(pur!=row_q-1'b1)begin stored_error_code<=5;state<=FAILED;end
     else begin slot_q<=pus;id_q<=pui;state<=DREQ;end
    end else if(prow)state<=HREQ;
    HREQ:if(accepted[4])state<=HWAIT;
    HWAIT:if(responded[4])begin high_bits<=response;state<=IREQ;end
    IREQ:if(accepted[4])state<=IWAIT;
    IWAIT:if(responded[4])begin ids_q<=response;state<=LOW;end
    LOW:if(vpready)begin
     if(vy!=row_q||vx!=x_q)begin stored_error_code<=5;state<=FAILED;end
     else state<=HIGH;
    end
    HIGH:if(vpready)begin
     if(x_q==158)begin x_q<=0;if(row_q==143)state<=FINISH;else begin row_q<=row_q+1'b1;state<=PWAIT;end end
     else begin x_q<=x_q+8'd2;state<=x_q[3:0]==14?HREQ:IREQ;end
    end
    FINISH:if(vd)begin release_bank<=3'b001<<bank_q;bank_q<=bank_q==2?2'd0:bank_q+1'b1;frame_done<=1;state<=IDLE;end
   endcase
   if(ce)begin stored_error_code<={1'b0,cc};state<=FAILED;end
   else if(be)begin stored_error_code<=6;state<=FAILED;end
   else if(pe)begin stored_error_code<=7;state<=FAILED;end
   else if(ve)begin stored_error_code<=8;state<=FAILED;end
  end
 end
endmodule
