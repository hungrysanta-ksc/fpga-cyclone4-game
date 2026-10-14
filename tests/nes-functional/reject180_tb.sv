// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module reject180_tb;
 reg clk=0,reset=1,active=0,fault=0,release_frame=0,collecting=0,owned=0,valid=0;
 always #23.280423 clk=~clk;
 reg [15:0] generation=0;reg [24:0] live_errors=0,final_errors=0;
 reg [8:0] scanline=0,dot=0;reg [7:0] mask=0,rows=0,objects=0,exceptions=0;
 reg [5:0] groups=0,palettes=0;
 wire sample_enable;wire [95:0] sample;
 nes_reject_witness180 witness(.*);
 reg ss=1,sck=0,mosi=0;wire selected,miso;
 nes_run_observer134 observer(.clk(clk),.reset(reset),.core_reset(!active),.cpu_sample(1'b0),.rom_fault(fault),
  .rom_error(4'd2),.ppu_fault_state154(64'h6082080028606060),.fault_trigger(fault),.fault_context(64'he200c2f430217a18),
  .history_sample157(sample),.history_enable180(sample_enable),.pad_event(1'b0),.pad_buttons(8'd0),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(selected),.miso(miso));
 reg [95:0] expected[0:63];integer expected_count=0,emissions=0;
 always @(posedge clk)if(!reset && active && sample_enable)emissions=emissions+1;
 reg [55:0] page;reg [95:0] got;
 task spi(input [7:0] cmd);
  reg [7:0] tx,rx;
  ss=0;#1500;page=0;
  for(integer x=0;x<8;x++)begin tx=x==0?cmd:0;rx=0;
   for(integer y=7;y>=0;y--)begin mosi=tx[y];#2000;sck=1;#2000;rx[y]=miso;sck=0;end
   if(x>0)page={page[47:0],rx};
  end
  ss=1;#1500;
 endtask
 task boot;
  @(negedge clk);reset=1;active=0;fault=0;owned=0;collecting=0;release_frame=0;
  live_errors=0;final_errors=0;expected_count=0;emissions=0;
  repeat(4)@(negedge clk);reset=0;active=1;
 endtask
 task begin_frame(input integer gen);
  release_frame=1;@(negedge clk);release_frame=0;owned=0;collecting=0;live_errors=0;final_errors=0;
  @(negedge clk);collecting=1;generation=gen;valid=0;
 endtask
 task seal(input bit good,input bit expect_event,input [8:0] first_y,first_x,input [7:0] first_mask);
  valid=good;owned=1;
  if(expect_event)begin
   expected[expected_count]={good?2'd2:2'd1,generation[7:0],final_errors,
     first_y,first_x,first_mask,rows,groups,objects,exceptions,palettes[5]?5'd31:palettes[4:0]};
   expected_count++;
  end
  @(negedge clk);repeat(9)@(negedge clk);
  if(emissions!=expected_count)$fatal(1,"emission count %0d != %0d gen%0d",emissions,expected_count,generation);
 endtask
 task error_at(input [24:0] err,input integer y,x,input [7:0] m);
  live_errors=err;scanline=y;dot=x;mask=m;@(negedge clk);
 endtask
 task check_ring(input integer flags);
  integer count,first,slot,base;
  active=0;repeat(4)@(negedge clk);spi(8'h77);
  count=expected_count>16?16:expected_count;first=expected_count&15;base=expected_count-count;
  if(page!=={8'he5,8'(flags),8'(count),8'(first),24'h016002})$fatal(1,"header %h count%0d",page,expected_count);
  for(integer i=0;i<count;i++)begin
   slot=(base+i)&15;spi(8'ha0|(slot<<1));got[95:48]=page[47:0];
   if(page[55:48]!=8'he5)$fatal(1,"page tag");
   spi(8'ha1|(slot<<1));got[47:0]=page[47:0];
   if(page[55:48]!=8'he5 || got!==expected[base+i])$fatal(1,"record%0d %h != %h",i,got,expected[base+i]);
  end
 endtask
 initial begin
  boot();spi(8'h77);if(page!==56'he5000000016002)$fatal(1,"empty");
  begin_frame(1);error_at(25'h80000,193,15,0);final_errors=25'h80000;seal(0,0,0,0,0); // prevalid ignored
  begin_frame(2);rows=224;groups=28;objects=7;exceptions=3;palettes=2;seal(1,0,0,0,0); // arm
  begin_frame(3);error_at(25'h80000,193,15,0);error_at(25'h88200,232,1,24);
  final_errors=25'h88200;rows=185;seal(0,1,193,15,0); // first position + final counts
  begin_frame(4);error_at(25'h80000,193,18,0);final_errors=25'h88200;seal(0,0,0,0,0); // jitter suppressed
  begin_frame(5);error_at(25'h480000,194,1,24);final_errors=25'h488200;seal(0,1,194,1,24); // error-vector change
  begin_frame(6);rows=224;seal(1,1,511,511,0); // recovery
  begin_frame(7);seal(1,0,0,0,0); // repeated good
  begin_frame(8);error_at(25'h80000,193,15,0);release_frame=1;@(negedge clk); // canceled error
  begin_frame(9);final_errors=0;rows=223;seal(0,1,511,511,0); // structural rejection, no live error
  begin_frame(10);live_errors=25'h80000;scanline=190;dot=30;mask=0;final_errors=25'h80000;
  seal(0,1,190,30,0); // first error and owned simultaneous
  // Twenty changing causes exercise retained event order beyond sixteen entries.
  for(integer k=0;k<20;k++)begin
   begin_frame(256+k);error_at(25'h80000,100+k,4,0);final_errors=25'h80001+k;palettes=40;
   seal(0,1,9'(100+k),9'd4,0);
  end
  check_ring(1);
  // STOP freezes even if the core restarts and emits additional candidates.
  active=1;begin_frame(500);error_at(25'h80000,55,4,0);final_errors=25'h80000;owned=1;
  repeat(5)@(negedge clk);check_ring(1);
  boot();begin_frame(1);seal(1,0,0,0,0);
  begin_frame(2);error_at(25'h80000,193,7,0);final_errors=25'h80000;fault=1;
  seal(0,1,193,7,0);fault=0;check_ring(3); // event at first fault retained
  spi(8'h71);if(page!==56'he501e200c2f430)$fatal(1,"fault context changed %h",page);
  spi(8'ha2);if(page!==0)$fatal(1,"unwritten entry visible");
  boot();fault=1;@(negedge clk);fault=0;check_ring(3); // freeze without event must not invent one
  $display("PASS180 witness transitions,first-position,seal-counts,jitter,cancel,wrap,SPI,STOP,fault,reset");$finish;
 end
 initial begin #60000000;$fatal(1,"watchdog");end
endmodule
