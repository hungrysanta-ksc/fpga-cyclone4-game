// Autonomous completed-frame consumer. All addresses are logical PSRAM words.
// Capture map is shared; IDs/dictionaries are banked. next-use at 420000,
// two palette events per row at 430000. Output sinks acknowledge COMMIT.
// Palette output is semantic data, not yet SNES HDMA table encoding.
module frame_pipeline_lcd(
 input wire clk,reset,start,lcd_on,pixel_valid,input wire[14:0]pixel_rgb,
 output wire armed,output wire[6:0]fifo_level,
 output wire error,output reg[3:0]error_code,
 output wire req_valid,req_write,output wire[22:0]req_addr,
 output wire[15:0]req_data,input wire req_ready,rsp_valid,input wire[15:0]rsp_data,
 output wire word_valid,input wire word_ready,
 output wire[14:0]word_addr,output wire[15:0]word_data,
 output wire palette_valid,input wire palette_ready,
 output wire palette_initial,output wire[7:0]palette_after_row,
 output wire[5:0]palette_slot,output wire[14:0]palette_rgb,
 output reg frame_done,output wire processing_bank
);
 localparam IDLE=0,CLEAR_REQ=1,CLEAR_WAIT=2,BSTART=3,BWAIT=4,
 INIT=5,PSTART=6,PWAIT=7,EWREQ=8,EWWAIT=9,DREQ=10,DWAIT=11,
 PALOUT=12,VSTART=13,ROW=14,ERREQ=15,ERWAIT=16,IREQ=17,IWAIT=18,
 LOW=19,HIGH=20,FINISH=21,FAILED=22;
 reg[4:0]state;
 reg bank_q;reg[8:0]count_q,clear_index;
 reg[5:0]slot_q;reg[7:0]id_q,row_q,x_q,event_row_q;
 reg event_second,event_write_second,initial_palette;
 reg[15:0]ids_q;reg[14:0]rgb_q;
 reg[1:0]release_bank;
 wire[1:0]banks;wire[8:0]count0,count1;
 wire ce;wire[2:0]cc;
 wire cv,cw;wire[22:0]ca;wire[15:0]cd;
 wire[4:0]accepted,responded;wire[15:0]response;
 capture_pingpong_lcd capture(clk,reset,start,lcd_on,pixel_valid,pixel_rgb,release_bank,
 banks,count0,count1,armed,ce,cc,cv,cw,accepted[0],ca,cd,responded[0],response,fifo_level);
 wire br,bw,bd,be,bb;wire[14:0]bra;wire[15:0]bwa,bwd;
 wire local_reset=reset||state==IDLE;
 next_use_builder builder(clk,local_reset,state==BSTART,count_q,
 br,accepted[1],bra,responded[1],response,bw,responded[2],bwa,bwd,bd,be,bb);
 wire pr,pu,pd,pe,pb;wire[15:0]pra;wire[7:0]pur,pui;wire[5:0]pus;
 reg planner_lane;
 wire[7:0]init_id={3'b0,slot_q}<count_q?{2'b0,slot_q}:8'd0;
 palette_planner planner(clk,local_reset,state==PSTART,count_q,state==INIT,
 slot_q,init_id,pr,accepted[3],pra,responded[3],planner_lane?response[15:8]:response[7:0],
 pu,state==EWWAIT&&responded[4],pur,pus,pui,pd,pe,pb);
 wire vpready,vd,ve,vb;wire[7:0]vy,vx;
 wire vpal=state==INIT||(state==PALOUT&&palette_ready&&!initial_palette);
 indexed_sixplane converter(clk,local_reset,state==VSTART,vpal,slot_q,
 state==INIT?init_id:id_q,state==LOW||state==HIGH,
 state==LOW?ids_q[7:0]:ids_q[15:8],vpready,vy,vx,
 word_valid,word_ready,word_addr,word_data,vd,ve,vb);
 wire own_req=state==CLEAR_REQ||state==EWREQ||state==DREQ||state==ERREQ||state==IREQ;
 wire own_write=state==CLEAR_REQ||state==EWREQ;
 wire[22:0]frame_base=23'h400000+(bank_q?23'h10000:23'd0);
 wire[22:0]own_addr=state==CLEAR_REQ ? 23'h430000+clear_index :
 state==EWREQ ? 23'h430000+{14'b0,pur,1'b0}+{22'b0,event_write_second} :
 state==ERREQ ? 23'h430000+{14'b0,(row_q-8'd1),1'b0}+{22'b0,event_second} :
 state==DREQ ? frame_base+23'hc000+id_q :
 frame_base+23'h8000+row_q*23'd80+{16'b0,x_q[7:1]};
 wire[15:0]own_data=state==CLEAR_REQ?16'd0:{1'b1,1'b0,pus,pui};
 video_router router(clk,reset,1'b0,{own_req,pr,bw,br,cv},
 {own_write,1'b0,1'b1,1'b0,cw},
 {own_addr,(23'h420000+{8'b0,pra[15:1]}),(23'h420000+{8'b0,bwa[15:1]}),
 (frame_base+23'h8000+{9'b0,bra[14:1]}),ca},
 {own_data,16'd0,bwd,16'd0,cd},accepted,responded,response,
 req_valid,req_write,req_addr,req_data,req_ready,rsp_valid,rsp_data);
 assign palette_valid=state==PALOUT;
 assign palette_initial=initial_palette;
 assign palette_after_row=row_q-8'd1;
 assign palette_slot=slot_q;assign palette_rgb=rgb_q;
 assign processing_bank=bank_q;
 assign error=ce||state==FAILED;
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;bank_q<=0;count_q<=0;clear_index<=0;slot_q<=0;id_q<=0;
   row_q<=0;x_q<=0;event_row_q<=255;event_second<=0;event_write_second<=0;
   initial_palette<=1;ids_q<=0;rgb_q<=0;release_bank<=0;frame_done<=0;
   error_code<=0;planner_lane<=0;
  end else begin
   release_bank<=0;frame_done<=0;
   if(accepted[3])planner_lane<=pra[0];
   case(state)
    IDLE:if(banks[bank_q])begin
     count_q<=bank_q?count1:count0;clear_index<=0;row_q<=0;x_q<=0;
     event_row_q<=255;event_write_second<=0;state<=CLEAR_REQ;
    end
    CLEAR_REQ:if(accepted[4])state<=CLEAR_WAIT;
    CLEAR_WAIT:if(responded[4])begin
     if(clear_index==287)state<=BSTART;
     else begin clear_index<=clear_index+1'b1;state<=CLEAR_REQ;end
    end
    BSTART:state<=BWAIT;
    BWAIT:if(bd)begin slot_q<=0;state<=INIT;end
    INIT:if(slot_q==63)state<=PSTART;else slot_q<=slot_q+1'b1;
    PSTART:state<=PWAIT;
    PWAIT:if(pu)begin
     if(event_row_q!=pur)begin event_write_second<=0;event_row_q<=pur;end
     state<=EWREQ;
    end else if(pd)begin slot_q<=0;id_q<=0;initial_palette<=1;state<=DREQ;end
    EWREQ:if(accepted[4])state<=EWWAIT;
    EWWAIT:if(responded[4])begin event_write_second<=1;state<=PWAIT;end
    DREQ:if(accepted[4])state<=DWAIT;
    DWAIT:if(responded[4])begin rgb_q<=response[14:0];state<=PALOUT;end
    PALOUT:if(palette_ready)begin
     if(initial_palette)begin
      if(slot_q==63)begin initial_palette<=0;state<=VSTART;end
      else begin slot_q<=slot_q+1'b1;id_q<=({3'b0,slot_q}+9'd1<count_q)?{2'b0,slot_q}+8'd1:8'd0;state<=DREQ;end
     end else if(!event_second)begin event_second<=1;state<=ERREQ;end
     else state<=IREQ;
    end
    VSTART:state<=ROW;
    ROW:if(vpready)begin
     if(vy!=row_q||vx!=0)begin error_code<=5;state<=FAILED;end
     else begin event_second<=0;state<=row_q==0?IREQ:ERREQ;end
    end
    ERREQ:if(accepted[4])state<=ERWAIT;
    ERWAIT:if(responded[4])begin
     if(response[15])begin slot_q<=response[13:8];id_q<=response[7:0];state<=DREQ;end
     else if(!event_second)begin event_second<=1;state<=ERREQ;end
     else state<=IREQ;
    end
    IREQ:if(accepted[4])state<=IWAIT;
    IWAIT:if(responded[4])begin ids_q<=response;state<=LOW;end
    LOW:if(vpready)state<=HIGH;
    HIGH:if(vpready)begin
     if(x_q==158)begin x_q<=0;if(row_q==143)state<=FINISH;else begin row_q<=row_q+1'b1;state<=ROW;end end
     else begin x_q<=x_q+8'd2;state<=IREQ;end
    end
    FINISH:if(vd)begin release_bank<=bank_q?2'b10:2'b01;bank_q<=!bank_q;frame_done<=1;state<=IDLE;end
   endcase
   if(ce)begin error_code<={1'b0,cc};state<=FAILED;end
   else if(be)begin error_code<=6;state<=FAILED;end
   else if(pe)begin error_code<=7;state<=FAILED;end
   else if(ve)begin error_code<=8;state<=FAILED;end
  end
 end
endmodule
