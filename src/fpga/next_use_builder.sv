// Prepare the following pair while the previous PSRAM write is outstanding.
// Keep one low-valid clock after each response for video_router rearming.
module next_use_builder (
 input wire clk_sys,reset,start,input wire[9:0]color_count,
 output wire req_valid,input wire req_ready,output wire[14:0]req_addr,
 input wire rsp_valid,input wire[15:0]rsp_ids,
 output wire write_valid,input wire write_ready,
 output wire[16:0]write_addr,output wire[15:0]write_data,output reg done,error,output wire busy
);
 localparam IDLE=0,CLEAR=1,REQUEST=2,RESPONSE=3,SCAN=4,PACK=5,WRITE=6,FAILED=7,HREQ=8,HRESP=9,SECOND=10;
 reg[3:0]state;reg[9:0]count_q;reg[7:0]row_q,x_q;reg[8:0]id_q;
 reg[14:0]row_base;reg[7:0]low_byte;
 reg pending_write;reg[15:0]word_q;reg[16:0]write_address;
 (* ramstyle="M9K" *) reg[7:0]nearest[0:511];
 reg[7:0]nearest_q;
 wire last_id={1'b0,id_q}+10'd1>=count_q;
 wire ends_word=id_q[0]||last_id;
 wire pack_step=state==PACK&&(!ends_word||!pending_write||write_ready);
 wire[8:0]nearest_read_addr=state==SCAN?id_q:id_q+9'd1;
 wire[7:0]value_q=nearest_q;
 wire[8:0]first_id=rsp_ids[8:0];

 wire valid_pixel=(state==RESPONSE&&rsp_valid&&{1'b0,first_id}<count_q);
 wire nearest_we=state==CLEAR||valid_pixel;
 wire[8:0]nearest_write_addr=state==CLEAR?id_q:first_id;
 wire[7:0]nearest_wdata=state==CLEAR?8'hff:row_q;
 // Single synchronous RAM read/write ports. A lookahead read addresses the
 // following ID, never the ID being updated on the same edge.
 always @(posedge clk_sys)begin
  if(nearest_we)nearest[nearest_write_addr]<=nearest_wdata;
  if(state==SCAN||(pack_step&&!last_id))nearest_q<=nearest[nearest_read_addr];
 end
 assign req_valid=state==REQUEST;
 assign req_addr=row_base+x_q;
 assign write_valid=pending_write;
 assign write_addr=write_address;
 assign write_data=word_q;
 assign busy=state!=IDLE&&state!=FAILED;
 always @(posedge clk_sys)begin
  if(reset)begin
   state<=IDLE;done<=0;error<=0;count_q<=0;row_q<=0;x_q<=0;id_q<=0;
   row_base<=0;low_byte<=0;word_q<=0;write_address<=0;pending_write<=0;
  end else begin
   done<=0;
   if(pending_write&&write_ready)pending_write<=0;
   if(start&&state==IDLE)begin
    error<=0;count_q<=color_count;id_q<=0;
    if(color_count==0||color_count>512)begin error<=1;state<=FAILED;end
    else state<=CLEAR;
   end else case(state)
    CLEAR:if(id_q==511)begin
     row_q<=143;row_base<=22880;x_q<=0;state<=REQUEST;
    end else id_q<=id_q+1'b1;
    REQUEST:if(req_ready)state<=RESPONSE;
    RESPONSE:if(rsp_valid)begin
     if({1'b0,first_id}>=count_q)begin
      error<=1;state<=FAILED;
     end else if(x_q==159)begin id_q<=0;state<=SCAN;end
     else begin x_q<=x_q+1'b1;state<=REQUEST;end
    end
    SCAN:state<=PACK;
    PACK:if(pack_step)begin
     if(ends_word)begin
      word_q<=id_q[0]?{value_q,low_byte}:{8'hff,value_q};
      write_address<={row_q,id_q[8:1],1'b0};pending_write<=1;
     end else low_byte<=value_q;
     if(last_id)state<=WRITE;
     else id_q<=id_q+1'b1;
    end
    WRITE:if(pending_write&&write_ready)begin
     if(row_q==0)begin done<=1;state<=IDLE;end
     else begin
      row_q<=row_q-1'b1;row_base<=row_base-15'd160;
      x_q<=0;state<=REQUEST;
     end
    end
    default:;
   endcase
  end
 end
endmodule
