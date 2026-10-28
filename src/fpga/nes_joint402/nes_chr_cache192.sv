// SPDX-License-Identifier: MIT
// Byte-data port retained. Tags/byte-valid use two18bit ports of one metadata
// RAM. Next-scan prefetch preserves one scan entry per clock; validity masks
// invalidate immediately and STOP never waits for a RAM clear sweep.
module nes_chr_cache192(
 input wire clk,reset,flush,request,input wire[31:0]content_epoch,input wire[21:0]address,input wire[15:0]generation,
 output wire ready,idle,response,error,output wire[21:0]response_address,output wire[15:0]response_generation,output wire[7:0]data,
 output wire back_request,back_abort,output wire[21:0]back_address,output wire[15:0]back_generation,
 input wire back_ready,back_idle,back_response,back_error,input wire[21:0]back_response_address,input wire[15:0]back_response_generation,input wire[7:0]back_data);
 (* ramstyle="M9K, no_rw_check" *)reg[7:0]bytes[0:127];
 (* ramstyle="M9K, no_rw_check" *)reg[17:0]metadata402[0:15];
 reg[17:0]tag_q402,valid_q402;reg[6:0]present402;
 reg[2:0]scan,slot,replacement;
 localparam IDLE=0,SCAN=1,HIT=2,MISS=3,WAIT=4,REPLY=5;
 reg[2:0]state;reg[31:0]cached_epoch;reg[21:0]held_address;reg[15:0]held_generation;reg[7:0]value,q;reg failed;
 wire invalidate=reset||flush||cached_epoch!=content_epoch;
 wire live=!invalidate,pending=state==WAIT;
 wire good=back_response&&!back_error&&back_response_address==held_address&&back_response_generation==held_generation;
 wire match402=present402[scan]&&valid_q402[15:0]!=0&&tag_q402==held_address[21:4];
 wire[2:0]next_scan402=state==SCAN&&!match402&&scan!=6?scan+1'b1:scan;
 wire[2:0]meta_read402=state==SCAN?next_scan402:(state==MISS||state==WAIT)?slot:3'd0;
 wire replace402=live&&state==SCAN&&!match402&&scan==6;
 // Each physical port uses one address for its read and write. Captured
 // read data during replacement/refill is not consumed in those states.
 wire[3:0]tag_address402={replace402?replacement:meta_read402,1'b0};
 wire[3:0]valid_address402={replace402?replacement:live&&pending&&good?slot:meta_read402,1'b1};
 always @(posedge clk)begin
  tag_q402<=metadata402[tag_address402];
  if(replace402)metadata402[tag_address402]<=held_address[21:4];
 end
 always @(posedge clk)begin
  valid_q402<=metadata402[valid_address402];
  if(replace402)metadata402[valid_address402]<=0;
  else if(live&&pending&&good)metadata402[valid_address402]<={2'd0,valid_q402[15:0]|(16'd1<<held_address[3:0])};
 end
 always @(posedge clk)begin
  q<=bytes[{next_scan402,held_address[3:0]}];
  if(live&&pending&&good)bytes[{slot,held_address[3:0]}]<=back_data;
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
   SCAN:if(match402)begin slot<=scan;state<=valid_q402[held_address[3:0]]?HIT:MISS;end
    else if(scan==6)begin slot<=replacement;present402[replacement]<=1;replacement<=replacement==6?0:replacement+1'b1;state<=MISS;end
    else scan<=scan+1'b1;
   HIT:begin value<=q;state<=REPLY;end
   MISS:if(back_ready)state<=WAIT;
   WAIT:if(back_response)begin value<=back_data;failed<=!good;state<=REPLY;end
   REPLY:state<=IDLE;
   default:begin failed<=1;state<=IDLE;end
  endcase
 end
endmodule
