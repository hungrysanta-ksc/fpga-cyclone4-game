// SPDX-License-Identifier: MIT
// Replaces the one-line CHR cache and owns capture lookup plus qualified miss.
// Caller holds request/address/generation until ready and aborts on lease or
// content-epoch loss. A new capture may fill the other bank during a query.
module nes_chr_cache611 (
 input wire clk,reset,stop,immutable,
 input wire start,seal,release_bank,input wire [15:0] capture_gen,release_gen,
 input wire sample,input wire [16:0] sample_address,input wire [7:0] sample_data,
 output wire start_ready,sample_ready,
 input wire request,request_obj,input wire [21:0] address,input wire [15:0] generation,
 output wire ready,idle,response,error,output wire [21:0] response_address,
 output wire [15:0] response_generation,output wire [7:0] data,
 output wire back_request,back_abort,output wire [21:0] back_address,
 output wire [15:0] back_generation,
 input wire back_ready,back_idle,back_response,back_error,
 input wire [21:0] back_response_address,input wire [15:0] back_response_generation,
 input wire [7:0] back_data
);
 localparam IDLE=0,LOOKUP=1,MISS=2,WAIT=3,BG_HIT=4;
 reg [2:0] state;
 reg held_obj;reg [7:0] bg_bytes[0:15];
 reg [15:0] bg_valid;reg [17:0] bg_tag;reg [7:0] bg_reply;
 wire bg_hit=bg_tag==address[21:4]&&bg_valid[address[3:0]];
 reg [21:0] held_address;
 reg [15:0] held_generation;
 wire kill=reset||stop||!immutable;
 reg [1:0] drain;
 always @(posedge clk or posedge kill)
  if(kill)drain<=2'b11;else drain<={drain[0],1'b0};
 wire live=!kill&&!drain[1];
 wire qready,qresponse,qhit;wire [7:0] qdata;
 // Cached bytes do not need the physical reader. Misses remain in MISS
 // until the arbiter grants them; idle still gates new tile admission.
 assign ready=live&&state==IDLE&&(request_obj?qready:(bg_hit||back_idle));
 assign idle=live&&state==IDLE&&back_idle;
 wire accept=request&&ready;
 nes_obj_capture611 capture(.clk(clk),.reset(reset),.stop(stop),.immutable(immutable),
  .start(start),.seal(seal),.release_bank(release_bank),
  .capture_gen(capture_gen),.release_gen(release_gen),
  .sample(sample),.sample_address(sample_address),.sample_data(sample_data),
  .start_ready(start_ready),.sample_ready(sample_ready),
  .query(accept&&request_obj),.query_gen(generation),.query_address(address[16:0]),
  .query_ready(qready),.response(qresponse),.hit(qhit),.data(qdata));
 assign back_request=live&&state==MISS;
 assign back_abort=!live;
 assign back_address=held_address;assign back_generation=held_generation;
 wire cached=state==LOOKUP&&qresponse&&qhit&&held_address[21:17]==5'h10;
 wire returned=state==WAIT&&back_response;
 assign response=live&&(cached||returned||state==BG_HIT);
 assign error=response&&returned&&(back_error||back_response_address!=held_address||
                                   back_response_generation!=held_generation);
 assign response_address=held_address;assign response_generation=held_generation;
 assign data=state==BG_HIT?bg_reply:cached?qdata:back_data;
 always @(posedge clk) begin
  if(accept)begin
   held_address<=address;held_generation<=generation;held_obj<=request_obj;
   if(!request_obj&&bg_hit)bg_reply<=bg_bytes[address[3:0]];
  end
  if(!live)bg_valid<=0;
  else if(returned&&!error&&!held_obj)begin
   bg_bytes[held_address[3:0]]<=back_data;bg_tag<=held_address[21:4];
   bg_valid<=(bg_tag==held_address[21:4]?bg_valid:16'b0)|(16'b1<<held_address[3:0]);
  end
  if(!live)state<=IDLE;
  else case(state)
   IDLE:if(accept)state<=request_obj?LOOKUP:bg_hit?BG_HIT:MISS;
   LOOKUP:if(qresponse)state<=cached?IDLE:MISS;
   MISS:if(back_ready)state<=WAIT;
   WAIT:if(back_response)state<=IDLE;
   BG_HIT:state<=IDLE;
  endcase
 end
endmodule
