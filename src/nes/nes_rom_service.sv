// SPDX-License-Identifier: MIT
// Original050 diagnostic immutable ROM service. All ports use NES master clk.
// Geometry: 64KiB PRG + up to32KiB CHR. Shared backend, one outstanding read.
// rom_request is a grant strobe ONLY when rom_ready, not a held valid signal.
// Backend must return address/data at least one edge AFTER acceptance, and flush
// pending replies on common reset. No asynchronous clock crossing is implemented.
module nes_rom_service(
 input wire clk,reset,
 input wire [24:0] cpumem_addr,input wire cpumem_read,cpu_sample,
 input wire [21:0] ppumem_addr,input wire ppumem_read,ppu_sample,
 output wire [7:0] cpu_data,ppu_data,output wire cpu_valid,ppu_valid,
 input wire rom_ready,output wire rom_request,output wire [21:0] rom_address,
 input wire rom_response,rom_error,input wire [21:0] rom_response_address,input wire [7:0] rom_data,
 output reg fault,output reg [3:0] error_code
);
 reg busy,pending_ppu;reg [21:0] pending_address;reg [7:0] age;
 reg cpu_cached,ppu_cached;reg [15:0] cpu_tag;reg [14:0] ppu_tag;reg [7:0] cpu_byte,ppu_byte;
 wire cpu_rom=cpumem_addr<25'h10000;
 wire ppu_rom=ppumem_addr>=22'h200000 && ppumem_addr<22'h208000;
 wire response_ok=busy && rom_response && !rom_error && rom_response_address==pending_address;
 wire cpu_reply=response_ok && !pending_ppu && pending_address==cpumem_addr[21:0];
 wire ppu_reply=response_ok && pending_ppu && pending_address==ppumem_addr;
 assign cpu_valid=!reset && !fault && cpu_rom && ((cpu_cached && cpu_tag==cpumem_addr[15:0]) || cpu_reply);
 assign ppu_valid=!reset && !fault && ppu_rom && ((ppu_cached && ppu_tag==ppumem_addr[14:0]) || ppu_reply);
 assign cpu_data=cpu_reply?rom_data:cpu_byte;
 assign ppu_data=ppu_reply?rom_data:ppu_byte;
 wire cpu_pending=busy && !pending_ppu && pending_address==cpumem_addr[21:0];
 wire ppu_pending=busy && pending_ppu && pending_address==ppumem_addr;
 wire cpu_need=cpumem_read && cpu_rom && !cpu_valid && !cpu_pending;
 wire ppu_need=ppumem_read && ppu_rom && !ppu_valid && !ppu_pending;
 // PPU has the shorter window. Never steal or abort an accepted CPU read.
 assign rom_request=!reset && !fault && rom_ready && (!busy || response_ok) && (ppu_need || cpu_need);
 assign rom_address=rom_request?(ppu_need?ppumem_addr:cpumem_addr[21:0]):pending_address;
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   busy<=0;pending_ppu<=0;pending_address<=0;age<=0;
   cpu_cached<=0;ppu_cached<=0;cpu_tag<=0;ppu_tag<=0;cpu_byte<=0;ppu_byte<=0;fault<=0;error_code<=0;
  end else if(!fault)begin
   if(busy)age<=age+1'b1;
   if(response_ok)begin
    busy<=0;
    if(pending_ppu)begin ppu_cached<=1;ppu_tag<=pending_address[14:0];ppu_byte<=rom_data;end
    else begin cpu_cached<=1;cpu_tag<=pending_address[15:0];cpu_byte<=rom_data;end
   end
   if(rom_request)begin busy<=1;pending_ppu<=ppu_need;pending_address<=rom_address;age<=0;end
   // One registered sticky cause. Deadline failure never stalls or slows NES.
   if(rom_response && !busy)begin fault<=1;error_code<=3;end
   else if(rom_response && rom_response_address!=pending_address)begin fault<=1;error_code<=4;end
   else if(rom_response && rom_error)begin fault<=1;error_code<=5;end
   else if(busy && !rom_response && age==255)begin fault<=1;error_code<=6;end
   else if(ppu_sample && ppu_rom && !ppu_valid)begin fault<=1;error_code<=2;end
   else if(cpu_sample && cpu_rom && !cpu_valid)begin fault<=1;error_code<=1;end
  end
 end
endmodule
