// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module history157_tb;
 reg clk=0,reset=1,active=0,fault=0,ss=1,sck=0,mosi=0;
 always #23.280423 clk=~clk;
 reg [95:0] sample=0;
 wire selected,miso;
 nes_run_observer134 dut(.clk(clk),.reset(reset),.core_reset(!active),.cpu_sample(1'b0),.rom_fault(fault),
  .rom_error(4'd2),.ppu_fault_state154(64'h6082080028606060),.fault_trigger(fault),.fault_context(64'he200c2f430217a18),
  .history_sample157(sample),.pad_event(1'b0),.pad_buttons(8'd0),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(selected),.miso(miso));
 reg [55:0] page,header;reg [95:0] got;integer i,j,slot;
 function [95:0] value(input integer n);
  value={9'd193,9'(n),12'(n^12'ha55),22'(22'h217a00+n),22'(22'h210000+n),22'(22'h217a00+n)};
 endfunction
 task spi(input [7:0] cmd);
  integer x,y;reg [7:0] tx,rx;begin
   ss=0;#150;page=0;
   for(x=0;x<8;x=x+1)begin tx=x==0?cmd:0;rx=0;
    for(y=7;y>=0;y=y-1)begin mosi=tx[y];#190;sck=1;#190;rx[y]=miso;sck=0;end
    if(x>0)page={page[47:0],rx};
   end
   ss=1;#150;
  end
 endtask
 task boot;
  begin @(negedge clk);reset=1;active=0;fault=0;repeat(4)@(negedge clk);reset=0;end
 endtask
 initial begin
  boot();spi(8'h77);if(page!==56'he0000000016001)$fatal(1,"empty %h",page);
  for(j=0;j<2;j=j+1)begin
   boot();active=1;
   for(i=0;i<37;i=i+1)begin sample=value(i);fault=(j==0 && i==36);@(negedge clk);end
   active=0;fault=0;repeat(4)@(negedge clk);
   spi(8'h77);header=page;
   if(page[55:48]!=8'he0||page[47:40]!=(j==0?3:1)||page[39:32]!=16||page[31:24]!=5||page[23:0]!=24'h016001)$fatal(1,"header %h",page);
   for(i=0;i<16;i=i+1)begin
    slot=(i+5)&15;spi(8'ha0|(slot<<1));got[95:48]=page[47:0];if(page[55:48]!=8'he0)$fatal;
    spi(8'ha1|(slot<<1));got[47:0]=page[47:0];
    if(page[55:48]!=8'he0||got!==value(i+21))$fatal(1,"order/faultedge i=%0d got=%h",i,got);
   end
   active=1;sample=0;repeat(20)@(negedge clk);active=0;
   spi(8'h77);if(page!==header)$fatal(1,"STOP changed history");
   spi(8'haa);got[95:48]=page[47:0];spi(8'hab);got[47:0]=page[47:0];if(got!==value(21))$fatal(1,"RAM mutated");
   if(j==0)begin spi(8'h71);if(page!==56'he001e200c2f430)$fatal(1,"old context changed %h",page);end
   spi(8'h76);if(page[55:48]!=8'he0 || page[39:24]!=0)$fatal(1,"pad page changed");
  end
  boot();active=1;sample=value(7);@(negedge clk);active=0;repeat(3)@(negedge clk);
  spi(8'h77);if(page!==56'he0010101016001)$fatal(1,"partial %h",page);
  spi(8'ha2);if(page!==0)$fatal(1,"unwritten RAM exposed");
  $display("PASS157 actual observer SPI,ring wrap,last16,first-fault edge,STOP,reset,partial,invalid-slot,old context/pad");$finish;
 end
 initial begin #10000000;$fatal(1,"watchdog");end
endmodule
