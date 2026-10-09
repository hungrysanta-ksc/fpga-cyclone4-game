// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module guard127_tb;
 reg mem_clk=0,ref_clk=0,reset=1,mem_run=1,ref_run=1;
 always #2.976 if(mem_run)mem_clk=~mem_clk;
 always #22.727 if(ref_run)ref_clk=~ref_clk;
 wire allow_memory,fault,local_reset,ready;
 nes_diag_clock_guard127 dut(.*);
 nes_domain_reset124 release_unit(.clk(mem_clk),.raw_reset(reset||!allow_memory),.reset(local_reset));
 nes_diag_startup_guard #(.WAIT_CYCLES(33603)) startup(.clk(mem_clk),.reset(local_reset),.ready(ready));
 realtime released;
 integer cases=0;
 task automatic ck(input bit ok,input string why);if(!ok)$fatal(1,"GUARD127 %s",why);endtask
 always @(negedge local_reset)released=$realtime;
 always @(posedge ready)ck($realtime-released>=200000,"startup below200us");
 task automatic fresh;
  reset=1;mem_run=1;ref_run=1;#100;reset=0;#210000;
  ck(allow_memory&&!fault&&ready,"normal startup");
 endtask
 initial begin
  fresh();mem_run=0;#4000;ck(fault&&!ready&&!allow_memory,"memory stopped");mem_run=1;#10000;ck(fault&&!ready,"sticky memory fault");cases++;
  fresh();ref_run=0;#5000;ck(fault&&!ready&&!allow_memory,"reference stopped");ref_run=1;#10000;ck(fault&&!ready,"sticky reference fault");cases++;
  fresh();mem_run=0;ref_run=0;#9000;ck(!fault&&ready,"both stopped counterexample retained");cases++;
  reset=1;#1;ck(!ready&&!allow_memory,"raw reset works without clocks");
  $display("PASS127 GUARD cases=%0d startup_min_ns=200000 both_stopped_unsafe=1",cases);$finish;
 end
 initial begin #1000000;$fatal(1,"GUARD127 watchdog");end
endmodule
