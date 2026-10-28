// SPDX-License-Identifier: MIT
// One TDP18 RAM: data0..111, tag/valid128..141. SCAN owns both metadata
// ports; on a hit B prefetches data for HIT. Refill writes byte/valid on A/B.
module nes_chr_cache192(
 input wire clk,reset,flush,request,input wire[31:0]content_epoch,input wire[21:0]address,input wire[15:0]generation,
 output wire ready,idle,response,error,output wire[21:0]response_address,output wire[15:0]response_generation,output wire[7:0]data,
 output wire back_request,back_abort,output wire[21:0]back_address,output wire[15:0]back_generation,
 input wire back_ready,back_idle,back_response,back_error,input wire[21:0]back_response_address,input wire[15:0]back_response_generation,input wire[7:0]back_data);
 (* ramstyle="M9K, no_rw_check" *)reg[17:0]storage402[0:143];
 reg[17:0]a_q402,b_q402;reg[6:0]present402;reg[2:0]scan,slot,replacement;
 localparam IDLE=0,SCAN=1,HIT=2,MISS=3,WAIT=4,REPLY=5;
 reg[2:0]state;reg[31:0]cached_epoch;reg[21:0]held_address;reg[15:0]held_generation;reg[7:0]value;reg failed;
 wire invalidate=reset||flush||cached_epoch!=content_epoch,live=!invalidate;
 wire good=back_response&&!back_error&&back_response_address==held_address&&back_response_generation==held_generation;
 wire match402=present402[scan]&&b_q402[15:0]!=0&&a_q402==held_address[21:4];
 wire hit402=state==SCAN&&match402&&b_q402[held_address[3:0]];
 wire[2:0]next_scan402=state==SCAN&&!match402&&scan!=6?scan+1'b1:scan;
 wire[2:0]meta_read402=state==SCAN?next_scan402:(state==MISS||state==WAIT)?slot:3'd0;
 wire replace402=live&&state==SCAN&&!match402&&scan==6,fill402=live&&state==WAIT&&good;
 wire[7:0]a_address402=replace402?8'd128+{replacement,1'b0}:fill402?{1'b0,slot,held_address[3:0]}:8'd128+{meta_read402,1'b0};
 wire[7:0]b_address402=replace402?8'd129+{replacement,1'b0}:fill402?8'd129+{slot,1'b0}:hit402?{1'b0,scan,held_address[3:0]}:8'd129+{meta_read402,1'b0};
 always @(posedge clk)begin
  a_q402<=storage402[a_address402];
  if(replace402||fill402)storage402[a_address402]<=replace402?held_address[21:4]:{10'd0,back_data};
 end
 always @(posedge clk)begin
  b_q402<=storage402[b_address402];
  if(replace402||fill402)storage402[b_address402]<=replace402?18'd0:{2'd0,b_q402[15:0]|(16'd1<<held_address[3:0])};
 end
 assign ready=live&&state==IDLE&&back_idle;assign idle=ready;
 assign response=live&&state==REPLY;assign error=failed;
 assign response_address=held_address;assign response_generation=held_generation;assign data=value;
 assign back_request=live&&state==MISS;assign back_abort=invalidate;
 assign back_address=held_address;assign back_generation=held_generation;
 always @(posedge clk)begin
  cached_epoch<=content_epoch;
  if(invalidate)begin state<=IDLE;scan<=0;slot<=0;replacement<=0;held_address<=0;held_generation<=0;value<=0;failed<=0;present402<=0;end
  else case(state)
   IDLE:if(request&&ready)begin held_address<=address;held_generation<=generation;scan<=0;failed<=0;state<=SCAN;end
   SCAN:if(match402)begin slot<=scan;state<=b_q402[held_address[3:0]]?HIT:MISS;end
    else if(scan==6)begin slot<=replacement;present402[replacement]<=1;replacement<=replacement==6?0:replacement+1'b1;state<=MISS;end
    else scan<=scan+1'b1;
   HIT:begin value<=b_q402[7:0];state<=REPLY;end
   MISS:if(back_ready)state<=WAIT;
   WAIT:if(back_response)begin value<=back_data;failed<=!good;state<=REPLY;end
   REPLY:state<=IDLE;
   default:begin failed<=1;state<=IDLE;end
  endcase
 end
endmodule
