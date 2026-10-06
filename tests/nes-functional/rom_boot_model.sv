// SPDX-License-Identifier: MIT
// Uninitialized diagnostic pin RAM. Only pin writes populate bytes, no readmemh.
`timescale 1ns/1ps
module rom_boot_model(input wire reset,input wire [21:0] psram_address,
 input wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble,inout wire [15:0] psram_data);
 reg [7:0] prg[0:65535],chr[0:32767];integer writes=0;realtime write_start;
 wire selected=(!psram_1ce ^ !psram_2ce);
 wire [23:0] base={psram_address,psram_1ce,1'b0};
 function automatic [7:0] value(input [23:0] a);
  if(a<24'h10000)value=prg[a[15:0]];else if(a>=24'h200000 && a<24'h208000)value=chr[a[14:0]];else value=8'hxx;
 endfunction
 assign #25 psram_data=selected && !psram_oe && psram_we?{psram_bhe?8'hzz:value(base),psram_ble?8'hzz:value(base+24'd1)}:16'hzzzz;
 task automatic store_byte(input [23:0] a,input [7:0] v);
  if(a<24'h10000)prg[a[15:0]]=v;else if(a>=24'h200000 && a<24'h208000)chr[a[14:0]]=v;else $fatal(1,"WRITE outside diagnostic ROM %h",a);
 endtask
 always @(negedge psram_we)if(!reset)begin
  if(!selected || !psram_oe)$fatal(1,"WRITE select/OE conflict");write_start=$realtime;
 end
 always @(posedge psram_we)if(!reset && selected)begin
  if($realtime-write_start<35.70)$fatal(1,"WRITE pulse too short");
  if(!psram_bhe)begin if($isunknown(psram_data[15:8]))$fatal(1,"WRITE unknown high byte");store_byte(base,psram_data[15:8]);writes++;end
  if(!psram_ble)begin if($isunknown(psram_data[7:0]))$fatal(1,"WRITE unknown low byte");store_byte(base+24'd1,psram_data[7:0]);writes++;end
 end
endmodule
