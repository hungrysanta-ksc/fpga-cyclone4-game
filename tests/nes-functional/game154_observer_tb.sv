// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module game154_observer_tb;
 reg clk=0,reset=1,core_reset=0,cpu_sample=0,rom_fault=0,fault_trigger=0;
 reg [3:0] rom_error=0;
 reg [63:0] fault_context=0,ppu_fault_state154=0;
 reg SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;wire selected,miso;
 always #23.28 clk=~clk;
 nes_run_observer134 dut(.*);
 integer checks=0;reg [7:0] rx;reg [63:0] got;
 localparam [63:0] PPU={9'd193,9'd237,1'b1,1'b0,1'b1,1'b0,5'b01000,5'b00000,14'h1210,8'h10,8'hff,1'b1,1'b0};
 task automatic ck(input bit ok,input string why);checks++;if(!ok)$fatal(1,"154 %s",why);endtask
 task automatic byte_io(input [7:0] tx,output [7:0] value);
  for(integer bitn=7;bitn>=0;bitn--)begin SPI_MOSI=tx[bitn];#2000;SPI_SCK=1;#1;value[bitn]=miso;#1999;SPI_SCK=0;end
 endtask
 task automatic page(input [7:0] op,output [55:0] value);
  reg [7:0] b;value=0;SPI_SS=0;#2000;byte_io(op,b);
  ck(selected,"aux command selected");
  for(integer n=0;n<7;n++)begin byte_io(0,b);value=(value<<8)|b;end
  #2000;SPI_SS=1;#1;ck(!selected,"raw CS release");#3000;
 endtask
 task automatic snapshot(input bit valid,input [63:0] expected);
  reg [55:0] hi,lo;page(8'h74,hi);page(8'h75,lo);
  ck(hi[55:48]==8'hdd&&lo[55:48]==8'hdd,"strict DD pair");
  ck(hi[47:40]==valid&&lo[47:40]==valid,"same first-event valid");
  got={hi[39:0],lo[39:16]};ck(got==expected,"64bit value across pages");
  ck(lo[15:8]==(valid?2:0)&&lo[7:0]==1,"cause/schema");
 endtask
 initial begin
  #200;@(negedge clk);reset=0;snapshot(0,0);
  @(negedge clk);fault_context=64'he200c2f420217a10;ppu_fault_state154=PPU;fault_trigger=1;
  @(posedge clk);#1;ppu_fault_state154=~PPU;fault_context=0;
  @(negedge clk);fault_trigger=0;rom_fault=1;rom_error=2;
  repeat(3)@(posedge clk);snapshot(1,PPU);
  ck(dut.first_context==64'he200c2f420217a10,"original address context retained");
  core_reset=1;snapshot(1,PPU); // STOP must not erase or overwrite observation.
  @(negedge clk);fault_trigger=1;ppu_fault_state154=0;
  @(negedge clk);fault_trigger=0;snapshot(1,PPU);
  @(negedge clk);reset=1;#200;@(negedge clk);reset=0;rom_fault=0;rom_error=0;snapshot(0,0);
  $display("PASS154 observer checks=%0d exact-edge/split-pages/STOP/first-fault/reset",checks);$finish;
 end
 initial begin #10000000;$fatal(1,"154 watchdog");end
endmodule
