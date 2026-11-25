// SPDX-License-Identifier: MIT
// Replaces the one-line CHR cache and owns capture lookup plus qualified miss.
// Caller holds request/address/generation until ready and aborts on lease or
// content-epoch loss. A new capture may fill the other bank during a query.
module nes_probe_order1022 #(parameter HELD_PLAN=0, parameter REMEMBER=0) (
 input wire clk,reset,stop,immutable,
 input wire start,seal,release_bank,input wire [15:0] capture_gen,release_gen,
 input wire sample,input wire [17:0] sample_address,input wire [7:0] sample_data,
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
 localparam IDLE=0,LOOKUP=1,MISS=2,WAIT=3,ALT=4,ALT_REPLY=5;
 reg [2:0] state;
 reg [21:0] saved_address;reg [15:0] saved_generation;
 // The external plan is leased through tile_done. tile205 holds its byte
 // index through WAIT; its STOP/fault cancels this port before the next plan.
 wire [21:0] held_address=HELD_PLAN?address:saved_address;
 wire [15:0] held_generation=HELD_PLAN?generation:saved_generation;
 wire kill=reset||stop||!immutable;
 reg [1:0] drain;
 always @(posedge clk or posedge kill)
  if(kill)drain<=2'b11;else drain<={drain[0],1'b0};
 wire live=!kill&&!drain[1];
 wire qready,qresponse,qhit;wire [7:0] qdata;
 // Cached bytes do not need the physical reader. Misses remain in MISS
 // until the arbiter grants them; idle still gates new tile admission.
 assign ready=live&&state==IDLE&&(request_obj?qready:back_idle);
 assign idle=live&&state==IDLE&&back_idle;
 wire accept=request&&ready;
 // A prediction changes lookup order only. Both ways check owner, tag and lane.
 reg last_mirror, reversed;
 reg [13:0] last_tile;
 wire first_mirror=REMEMBER && last_mirror && address[17:4]==last_tile;
 wire probe_mirror=state==ALT ? !reversed : first_mirror;
 nes_obj_cross1022 capture(.clk(clk),.reset(reset),.stop(stop),.immutable(immutable),
  .start(start),.seal(seal),.release_bank(release_bank),
  .capture_gen(capture_gen),.release_gen(release_gen),
  .sample(sample),.sample_address(sample_address),.sample_data(sample_data),
  .start_ready(start_ready),.sample_ready(sample_ready),
  .alternate(probe_mirror),.query((accept&&request_obj)||state==ALT),
  .query_gen(state==ALT?held_generation:generation),
  .query_address(state==ALT?held_address[17:0]:address[17:0]),
  .query_ready(qready),.response(qresponse),.hit(qhit),.data(qdata));
 assign back_request=live&&state==MISS;
 assign back_abort=!live;
 assign back_address=held_address;assign back_generation=held_generation;
 wire cached=(state==LOOKUP||state==ALT_REPLY)&&qresponse&&qhit&&held_address[21:18]==4'h8;
 wire returned=state==WAIT&&back_response;
 assign response=live&&(cached||returned);
 assign error=response&&returned&&(back_error||back_response_address!=held_address||
                                   back_response_generation!=held_generation);
 assign response_address=held_address;assign response_generation=held_generation;
 assign data=cached?qdata:back_data;
 always @(posedge clk) begin
  if(!live || start || release_bank || seal) last_mirror<=0;
  else if(cached) begin
   last_mirror<=(state==LOOKUP)?reversed:!reversed;
   last_tile<=held_address[17:4];
  end
  if(accept) reversed<=first_mirror;
  if(accept)begin
   saved_address<=address;saved_generation<=generation;
  end
  if(!live)state<=IDLE;
  else case(state)
   IDLE:if(accept)state<=request_obj?LOOKUP:MISS;
   LOOKUP:if(qresponse)state<=cached?IDLE:ALT;
   ALT:if(qready)state<=ALT_REPLY;
   ALT_REPLY:if(qresponse)state<=cached?IDLE:MISS;
   MISS:if(back_ready)state<=WAIT;
   WAIT:if(back_response)state<=IDLE;
  endcase
 end
endmodule
