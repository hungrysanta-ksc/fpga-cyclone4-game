// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module diag_startup_guard_tb;
 reg clk=0,reset=1,enable=1;integer half=62;realtime half_ns=62.5;
 always #(half_ns)if(enable)clk=~clk;
 wire ready;nes_diag_startup_guard dut(.*);
 realtime released,first_edge;integer edges=0;
 task automatic await_ready;
  edges=0;released=$realtime;
  while(!ready)begin @(posedge clk);#0.001;edges++;
   if(edges>1602)$fatal(1,"STARTUP_NOT_BOUNDED");
  end
  if(edges!=1601)$fatal(1,"STARTUP_EDGE_COUNT got=%0d",edges);
  if($realtime-released<150000)$fatal(1,"STARTUP_BEFORE_150US elapsed=%0f",$realtime-released);
 endtask
 initial begin
  if($value$plusargs("HALF=%d",half))half_ns=half;
  repeat(3)@(negedge clk);reset=0;await_ready();
  // Ready remains stable after the saturation point.
  repeat(5)@(negedge clk);if(!ready)$fatal(1,"READY_NOT_STICKY");
  enable=0;reset=1;#1;if(ready)$fatal(1,"RESET_NOT_ASYNC");
  #1000;enable=1;repeat(3)@(negedge clk);reset=0;
  repeat(25)@(negedge clk);enable=0;#2000000;
  if(ready)$fatal(1,"STOPPED_CLOCK_EARLY_READY");
  // A reset during this stalled warmup must discard elapsed cycles.
  reset=1;#1000;enable=1;repeat(3)@(negedge clk);reset=0;await_ready();
  $display("PASS_STARTUP_GUARD half=%0f full_intervals=1600 resets=2 stalled_warmup=1",half_ns);$finish;
 end
 initial begin #10000000;$fatal(1,"WATCHDOG");end
endmodule
