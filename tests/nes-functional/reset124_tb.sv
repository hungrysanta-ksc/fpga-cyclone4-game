// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module reset124_tb;
 reg clk=0,running=1,raw_reset=1;
 wire reset;
 nes_domain_reset124 dut(.*);
 always #5 if(running)clk=~clk;
 reg [7:0] observable;
 always @(posedge clk or posedge reset)
  if(reset)observable<=0;else observable<=observable+1'b1;
 integer checks=0;
 task automatic check(input bit ok);
  if(!ok)$fatal(1,"RESET124 contract check=%0d",checks);
  checks++;
 endtask
 task automatic release_check;
  // A raw deassertion must not expose operation without local clock edges.
  raw_reset=0;#0.001;check(reset && observable==0);
  @(posedge clk);#0.001;check(reset && observable==0);
  @(posedge clk);#0.001;check(!reset && observable==0);
  @(posedge clk);#0.001;check(observable==1);
 endtask
 initial begin
  #12;release_check();
  repeat(10)@(negedge clk);
  running=0;#1;raw_reset=1;#0.001;check(reset && observable==0);
  #0.099;raw_reset=0;#50;check(reset && observable==0);
  running=1;
  @(posedge clk);#0.001;check(reset && observable==0);
  @(posedge clk);#0.001;check(!reset && observable==0);
  @(posedge clk);#0.001;check(observable==1);
  // Assertion between edges cancels active state without waiting for a clock.
  #1;raw_reset=1;#0.001;check(reset && observable==0);
  #0.099;release_check();
  $display("PASS RESET124 checks=%0d stopped_clock_short_pulse=1",checks);$finish;
 end
 initial begin #10000;$fatal(1,"RESET124 timeout");end
endmodule
