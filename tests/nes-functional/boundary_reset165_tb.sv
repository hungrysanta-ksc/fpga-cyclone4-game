// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module boundary_reset_case #(parameter WIDTH=96, parameter REVERSE=0, parameter real PHASE=0)(output reg done=0);
 reg src_clk=0,dst_clk=0,src_run=1,dst_run=1,reset=1;
 localparam real SRC_HALF=REVERSE?5.952381:22.727273;
 localparam real DST_HALF=REVERSE?22.727273:5.952381;
 always #(SRC_HALF)if(src_run)src_clk=~src_clk;
 initial begin #(PHASE);forever begin #(DST_HALF);if(dst_run)dst_clk=~dst_clk;end end
 reg src_valid=0,dst_ready=0;reg [WIDTH-1:0] src_data=0;
 wire src_ready,dst_valid;wire [WIDTH-1:0] dst_data;
 nes_native_mailbox165 #(.WIDTH(WIDTH)) dut(.*);
 integer delivered=0,resets=0,stopped=0;
 task fresh;
  reset=1;src_valid=0;dst_ready=0;#0.1;
  if(src_ready||dst_valid)$fatal(1,"raw reset did not quarantine");
  #101.7;reset=0;resets++;
  repeat(12)@(negedge src_clk);
  if(dst_valid)$fatal(1,"stale packet after common reset");
 endtask
 task offer(input integer value);
  wait(src_ready);@(negedge src_clk);src_data=WIDTH'(96'hfeed0123456789abcdef000000^value);src_valid=1;
  @(negedge src_clk);src_valid=0;
 endtask
 task receive(input integer value,input integer stall);
  wait(dst_valid);
  repeat(stall+1)begin
   @(negedge dst_clk);
   if(!dst_valid||dst_data!==WIDTH'(96'hfeed0123456789abcdef000000^value))$fatal(1,"lost/torn/duplicate payload");
   if(src_ready)$fatal(1,"source reused before ACK");
  end
  dst_ready=1;@(negedge dst_clk);dst_ready=0;delivered++;
  wait(src_ready);@(negedge dst_clk);if(dst_valid)$fatal(1,"ACK did not consume");
 endtask
 // Recovery targets must be the local release, even during an empty transfer.
 always @(negedge src_clk)if(dut.src_reset&&(dut.request!==0||dut.held!=='0))$fatal(1,"source local reset");
 always @(negedge dst_clk)if(dut.dst_reset&&(dut.valid!==0||dut.capture!==0||dut.acknowledge!==0))$fatal(1,"destination local reset");
 initial begin
  fresh();
  for(integer n=0;n<64;n++)begin offer(n);receive(n,n%7);end
  // Cancel every control/capture/ACK phase, then demand a fresh generation.
  for(integer phase=0;phase<9;phase++)begin
   offer(100+phase);repeat(phase)@(negedge dst_clk);fresh();
   offer(200+phase);receive(200+phase,2);
  end
  // Either clock can halt. Common reset must hold the stopped endpoint down.
  for(integer side=0;side<2;side++)begin
   offer(300+side);@(negedge src_clk);@(negedge dst_clk);
   if(side==0)src_run=0;else dst_run=0;
   reset=1;src_valid=0;dst_ready=0;#83.3;reset=0;#401.1;
   if(src_ready||dst_valid)$fatal(1,"stopped endpoint escaped reset");
   if(side==0&&(!dut.src_reset||dut.held!=='0))$fatal(1,"stopped source reset");
   if(side==1&&(!dut.dst_reset||dut.valid!==0))$fatal(1,"stopped destination reset");
   src_run=1;dst_run=1;stopped++;fresh();offer(400+side);receive(400+side,3);
  end
  done=1;$display("PASS BOUNDARY165 width=%0d reverse=%0d phase=%0f delivered=%0d resets=%0d stopped=%0d",WIDTH,REVERSE,PHASE,delivered,resets,stopped);
 end
 initial begin #2000000;$fatal(1,"boundary watchdog");end
endmodule
module boundary_reset165_tb;
 wire [5:0] done;
 boundary_reset_case #(96,0,0.0) a(done[0]);
 boundary_reset_case #(96,0,1.7) b(done[1]);
 boundary_reset_case #(96,0,10.1) c(done[2]);
 boundary_reset_case #(17,1,0.0) d(done[3]);
 boundary_reset_case #(17,1,7.8) e(done[4]);
 boundary_reset_case #(17,1,42.1) f(done[5]);
 initial begin wait(&done);$display("PASS BOUNDARY165 all six cases");$finish;end
endmodule
