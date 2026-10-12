// SPDX-License-Identifier: MIT
// One reader, unchanged core priority. Fill is admitted only in a qualified
// NTSC/MMC3 vblank CPU-cache-hit slot; this is NOT an arbitrary idle arbiter.
// Reset MUST also reset the physical reader. Abort drains without resetting it.
module nes_native_arbiter165(
 input wire clk,reset,slot,core_safe,
 input wire core_request,input wire [21:0] core_address,
 output wire core_ready,core_response,core_error,
 output wire [21:0] core_response_address,output wire [7:0] core_data,
 input wire fill_request,fill_abort,input wire [21:0] fill_address,input wire [15:0] fill_generation,
 output wire fill_ready,fill_idle,fill_response,fill_error,
 output wire [21:0] fill_response_address,output wire [15:0] fill_response_generation,output wire [7:0] fill_data,
 input wire mem_ready,mem_response,mem_error,input wire [21:0] mem_response_address,input wire [7:0] mem_data,
 output wire mem_request,output wire [21:0] mem_address,output reg fault
);
 reg owner,discard;reg [21:0] held_address;reg [15:0] held_generation;reg [3:0] age;
 wire grant=fill_request && fill_ready;
 assign core_ready=!reset && !owner && mem_ready;
 assign fill_ready=!reset && !fault && !owner && !fill_abort && slot && core_safe && !core_request && mem_ready;
 assign mem_request=!reset && (core_request || grant);
 assign mem_address=grant?fill_address:core_address;
 assign core_response=!reset && !owner && mem_response;
 assign core_error=mem_error;assign core_response_address=mem_response_address;assign core_data=mem_data;
 assign fill_response=!reset && owner && !discard && !fill_abort && mem_response;
 assign fill_error=mem_error || fault;
 assign fill_response_address=mem_response_address;assign fill_response_generation=held_generation;assign fill_data=mem_data;
 // Core traffic is separate. No queued or future fill reply can exist once
 // owner is clear and the common-reset reader has returned readiness.
 assign fill_idle=!reset && !owner && mem_ready;
 always @(posedge clk or posedge reset)begin
  if(reset)begin owner<=0;discard<=0;held_address<=0;held_generation<=0;age<=0;fault<=0;end
  else begin
   if(owner)begin
    if(age!=15)age<=age+1'b1;
    if(fill_abort)discard<=1;
    // Seven NES-edge bound is conditional on unchanged 168MHz/READ16 reader.
    // A lost reply never releases ownership onto a still-active PSRAM cycle.
    if(!mem_response && age>=6)fault<=1;
    if(mem_response)begin
     owner<=0;
     if(mem_error || mem_response_address!=held_address)fault<=1;
    end
   end
   if(grant)begin owner<=1;discard<=0;age<=0;held_address<=fill_address;held_generation<=fill_generation;end
  end
 end
endmodule
