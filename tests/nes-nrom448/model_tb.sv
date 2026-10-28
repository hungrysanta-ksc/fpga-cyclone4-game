// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module nrom448_tb;
 reg reset=1,ce1=1,ce2=1,oe=1,we=1,bhe=1,ble=1,drive=0;
 reg [21:0] address=0;reg [15:0] output_data=0;
 tri [15:0] data;assign data=drive?output_data:16'hzzzz;
 rom_boot_full_model ram(.reset(reset),.psram_address(address),.psram_1ce(ce1),.psram_2ce(ce2),.psram_oe(oe),.psram_we(we),.psram_bhe(bhe),.psram_ble(ble),.psram_data(data));
 task automatic put(input [23:0] a,input [7:0] v);
  address=a[23:2];ce1=a[1];ce2=!a[1];bhe=a[0];ble=!a[0];output_data={v,v};drive=1;#50;we=0;#100;we=1;#20;ce1=1;ce2=1;drive=0;#30;
 endtask
 task automatic check(input [23:0] a,input [7:0] v);
  address=a[23:2];ce1=a[1];ce2=!a[1];bhe=0;ble=0;oe=0;#60;
  if((a[0]?data[7:0]:data[15:8])!==v)$fatal(1,"read mismatch address=%h data=%h expected=%h",a,data,v);
  oe=1;ce1=1;ce2=1;#40;
 endtask
 initial begin
  #10;reset=0;#10;put(24'h000000,8'h12);put(24'h000001,8'h34);put(24'h010000,8'h56);put(24'h03fffe,8'h78);put(24'h03ffff,8'h9a);
  put(24'h200000,8'hbc);put(24'h200001,8'hde);put(24'h208000,8'hf1);put(24'h21fffe,8'h35);put(24'h21ffff,8'h79);
  check(24'h000000,8'h12);check(24'h000001,8'h34);check(24'h010000,8'h56);check(24'h03fffe,8'h78);check(24'h03ffff,8'h9a);
  check(24'h200000,8'hbc);check(24'h200001,8'hde);check(24'h208000,8'hf1);check(24'h21fffe,8'h35);check(24'h21ffff,8'h79);
  if(ram.writes!=10)$fatal(1,"write count");$display("PASS NROM448 full PRG/CHR pin model boundaries and lanes");$finish;
 end
endmodule
