// SPDX-License-Identifier: MIT
// Test-only pin memory. Access delay is an assumption, not a part specification.
`timescale 1ns/1ps
module rom_physical_model #(parameter realtime ACCESS_NS=25.0,parameter integer FIXTURE=0)(
 input wire [21:0] psram_address,
 input wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble,
 output wire [15:0] psram_data
);
 reg [7:0] prg[0:65535],chr[0:32767];
 integer chr32,unused;
 initial if(FIXTURE)begin
  unused=$value$plusargs("CHR32=%d",chr32);
  $readmemh("prg.hex",prg);$readmemh("chr.hex",chr,0,chr32?32767:16383);
 end
 function automatic [7:0] value(input [23:0] address);
  if(FIXTURE)begin
   if(address<24'h010000)value=prg[address[15:0]];
   else if(address>=24'h200000 && address<24'h208000)value=chr[address[14:0]];
   else value=8'hxx;
  end else value=address[7:0]^address[15:8]^{address[19:16],address[23:20]}^8'hb7;
 endfunction
 wire selected=(!psram_1ce ^ !psram_2ce) && !psram_oe && psram_we;
 wire [23:0] base={psram_address,psram_1ce,1'b0};
 assign #(ACCESS_NS) psram_data=selected?{psram_bhe?8'hzz:value(base),psram_ble?8'hzz:value(base+24'd1)}:16'hzzzz;
endmodule
