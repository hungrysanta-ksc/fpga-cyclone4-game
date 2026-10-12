// SPDX-License-Identifier: MIT
// Bounded NES-clock CHR stream for a SEALED physical required set.
// This module is not wired to the production PSRAM arbiter. Its backend must
// preserve CPU/PPU deadlines and acknowledge flush before a cancelled request
// can be reused. Bytes are tentative until done && success for this generation.
module nes_native_fill165 #(
 parameter integer MAX_TILES=512,
 parameter integer MAX_CYCLES=262144,
 parameter integer WAIT_CYCLES=1024
)(
 input wire clk,reset,start,clear,
 input wire frame_owned,geometry_valid,input wire [15:0] frame_generation,
 output wire query,output wire [2:0] query_kind,output wire [12:0] query_index,
 output wire [15:0] query_generation,input wire response,hit,input wire [63:0] data,
 // mem_idle is a backend FLUSH acknowledgement: no future old reply remains.
 input wire mem_idle,mem_ready,mem_response,mem_error,
 input wire [21:0] mem_response_address,input wire [15:0] mem_response_generation,
 input wire [7:0] mem_data,
 output wire mem_request,mem_abort,output wire [21:0] mem_address,output wire [15:0] mem_generation,
 output wire byte_valid,input wire byte_ready,output wire [7:0] byte_data,
 output wire [12:0] byte_tile,output wire [3:0] byte_lane,output wire [1:0] byte_kind,
 output wire [15:0] byte_generation,
 output reg busy,done,quarantine,output wire success,output reg [3:0] error,
 output reg [9:0] tile_count,output reg [13:0] byte_count,output reg [31:0] cycles
);
 localparam IDLE=0,ASK=1,LOOKUP=2,REQUEST=3,WAIT_REPLY=4,STREAM=5;
 reg [2:0] state;reg [12:0] tile;reg [3:0] lane;reg [1:0] kind;
 reg [15:0] generation;reg [7:0] held_byte;reg pending,completed;reg [31:0] waiting;
 wire lease_ok=frame_owned && geometry_valid && frame_generation==generation;
 wire time_ok=cycles<MAX_CYCLES && waiting<WAIT_CYCLES;
 wire operate=busy && lease_ok && !reset && !clear && !quarantine && time_ok;
 assign success=completed && lease_ok && !reset && !clear && !quarantine;
 assign query=operate && state==ASK;
 assign query_kind=3'd6;assign query_index=tile;assign query_generation=generation;
 assign mem_request=operate && state==REQUEST && !mem_response;
 assign mem_address={5'h10,tile,lane};assign mem_generation=generation;
 assign mem_abort=quarantine || ((reset || clear || (busy&&!lease_ok) || (busy&&!time_ok)) && pending);
 assign byte_valid=operate && state==STREAM;
 assign byte_data=held_byte;assign byte_tile=tile;assign byte_lane=lane;
 assign byte_kind=kind;assign byte_generation=generation;
 task fail(input [3:0] reason);
  begin
   busy<=0;done<=1;completed<=0;error<=reason;state<=IDLE;
   if(pending)quarantine<=1;
  end
 endtask
 task advance_tile;
  begin
   waiting<=0;
   if(tile==8191)begin busy<=0;done<=1;completed<=1;state<=IDLE;end
   else begin tile<=tile+1'b1;state<=ASK;end
  end
 endtask
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;busy<=0;done<=0;completed<=0;error<=0;tile<=0;lane<=0;kind<=0;generation<=0;
   tile_count<=0;byte_count<=0;cycles<=0;waiting<=0;held_byte<=0;pending<=0;
   // Even reset must obtain a flush acknowledgement before issuing requests.
   quarantine<=1;
  end else begin
   if(quarantine && mem_idle)begin quarantine<=0;pending<=0;end
   if(clear)begin
    busy<=0;done<=0;completed<=0;error<=0;state<=IDLE;
    if(pending)quarantine<=1;
   end else if(!busy)begin
    if(done && completed && !lease_ok)begin completed<=0;error<=2;end
    else if(start && !done && !quarantine && mem_idle)begin
     if(!frame_owned || !geometry_valid)begin done<=1;completed<=0;error<=1;end
     else begin
      busy<=1;completed<=0;error<=0;generation<=frame_generation;tile<=0;lane<=0;
      tile_count<=0;byte_count<=0;cycles<=0;waiting<=0;state<=ASK;
     end
    end
   end else begin
    cycles<=cycles+1'b1;waiting<=waiting+1'b1;
    if(!lease_ok)fail(2);
    else if(cycles>=MAX_CYCLES)fail(3);
    else if(waiting>=WAIT_CYCLES)fail(4);
    else if(mem_response && state!=WAIT_REPLY)begin fail(8);quarantine<=1;end
    else case(state)
     ASK:begin state<=LOOKUP;waiting<=0;end
     LOOKUP:if(response)begin
      waiting<=0;
      if(!hit || data[63:2]!=0)fail(5);
      else if(data[1:0]==0)advance_tile();
      else if(tile_count>=MAX_TILES)fail(6);
      else begin tile_count<=tile_count+1'b1;kind<=data[1:0];lane<=0;state<=REQUEST;end
     end
     REQUEST:if(mem_ready)begin pending<=1;state<=WAIT_REPLY;waiting<=0;end
     WAIT_REPLY:if(mem_response)begin
      pending<=0;waiting<=0;
      if(mem_error || mem_response_address!=mem_address || mem_response_generation!=generation)begin
       fail(7);quarantine<=1;
      end else begin held_byte<=mem_data;state<=STREAM;end
     end
     STREAM:if(byte_ready)begin
      byte_count<=byte_count+1'b1;waiting<=0;
      if(lane==15)advance_tile();
      else begin lane<=lane+1'b1;state<=REQUEST;end
     end
     default:fail(9);
    endcase
   end
  end
 end
endmodule
