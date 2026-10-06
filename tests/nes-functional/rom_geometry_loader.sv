// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module rom_geometry_loader(output reg done=0);
 reg mem_clk=0,reset=1,load_begin=0,load_chr32=0,load_valid=0,load_end=0,start=0,stop=0;
 reg [7:0] load_data=0;
 always #5.952381 mem_clk=~mem_clk;
 wire load_ready,loaded,run_enable,fault,rom_chr32;
 wire [3:0] error_code;wire [16:0] loaded_bytes;
 wire [21:0] load_address;wire [15:0] load_pin_data;
 wire load_drive,load_1ce,load_2ce,load_oe,load_we,load_bhe,load_ble;
 nes_rom_loader dut(.*);
 integer checks=0,bytes=0;
 task automatic check(input bit ok);checks++;if(!ok)$fatal(1,"Loader geometry check%0d",checks);endtask
 task automatic fresh;
  @(negedge mem_clk);reset=1;load_begin=0;load_valid=0;load_end=0;start=0;stop=0;
  repeat(3)@(negedge mem_clk);reset=0;repeat(3)@(negedge mem_clk);
  check(rom_chr32===0&&!run_enable&&!loaded&&!fault);
 endtask
 task automatic begin_image(input bit chr32);
  load_chr32=chr32;load_begin=1;@(negedge mem_clk);load_begin=0;
  check(rom_chr32===chr32&&load_ready);
 endtask
 initial begin
  integer total;
  for(integer mode=0;mode<2;mode++)begin
   fresh();begin_image(mode!=0);total=mode?98304:81920;
   // Change the caller argument throughout loading. The accepted register
   // must continue to determine BOTH exposed geometry and exact byte count.
   load_chr32=mode==0;
   for(integer i=0;i<total;i++)begin
    check(load_ready&&rom_chr32===(mode!=0));load_valid=1;load_data=i[7:0];
    @(negedge mem_clk);load_valid=0;
    repeat(5)@(negedge mem_clk);
    check(loaded_bytes==i+1&&!fault);bytes++;
   end
   check(!load_ready&&!loaded&&!run_enable);
   load_end=1;@(negedge mem_clk);load_end=0;
   check(loaded&&!run_enable&&rom_chr32===(mode!=0));
   start=1;@(negedge mem_clk);start=0;
   check(run_enable&&rom_chr32===(mode!=0));
   stop=1;@(negedge mem_clk);stop=0;
   check(loaded&&!run_enable&&rom_chr32===(mode!=0));
   start=1;@(negedge mem_clk);start=0;check(run_enable);
   // Rejected BEGIN during RUN may assert a fault, never change geometry.
   load_begin=1;@(negedge mem_clk);load_begin=0;
   check(fault&&error_code==1&&!run_enable&&rom_chr32===(mode!=0));
   fresh();begin_image(mode==0);check(rom_chr32===(mode==0));
  end
  $display("PASS LOADER GEOMETRY checks=%0d bytes=%0d modes=2 run_rebegin_rejected=2",checks,bytes);
  done=1;
 end
endmodule
