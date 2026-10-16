// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module source_epoch205_tb;
 reg mem_clk=0,nes_clk=0,run_clock=1,reset=1,begin_load=0,write_byte=0,loaded=0,run=0,fail=0;
 reg [18:0] count=0;wire ready,isrom,writing;wire [31:0] epoch;
 always #2.976 mem_clk=!mem_clk;
 always #23.28 if(run_clock)nes_clk=!nes_clk;
 nes_source_epoch205 dut(.mem_clk(mem_clk),.nes_clk(nes_clk),.reset(reset),.load_begin(begin_load),.load_valid(write_byte),
 .loaded(loaded),.run_enable(run),.loader_fault(fail),.loaded_bytes(count),.source_ready(ready),.source_is_rom(isrom),.source_writing(writing),.live_epoch(epoch));
 always @(negedge nes_clk)if(!reset)begin
  if(ready && (writing||!isrom||!dut.admitted||dut.held))$fatal(1,"bad local admission");
 end
 integer checks=0;reg [31:0] prior;
 task wait_ready;
  begin repeat(8)@(negedge nes_clk);if(!ready||!isrom||writing)$fatal(1,"not admitted");checks++;end
 endtask
 task begin_rom;
  begin @(negedge mem_clk);loaded=0;run=0;count=0;begin_load=1;
   #1;if(ready)$fatal(1,"BEGIN exposed old epoch");checks++;
   @(negedge mem_clk);begin_load=0;repeat(5)@(negedge mem_clk);
  end
 endtask
 initial begin
  repeat(5)@(negedge mem_clk);reset=0;repeat(8)@(negedge nes_clk);
  if(ready||isrom||!writing)$fatal(1,"empty admitted");checks++;
  begin_rom();count=19'h5ffff;loaded=1;run=1;repeat(8)@(negedge nes_clk);
  if(ready)$fatal(1,"incomplete ROM");checks++;
  count=19'h60000;wait_ready();if(epoch!=1)$fatal(1,"first epoch");checks++;
  prior=epoch;run=0;#1;if(ready)$fatal(1,"STOP late");checks++;
  repeat(4)@(negedge nes_clk);run=1;wait_ready();if(epoch!=prior)$fatal(1,"STOP changed content");checks++;
  // Invalidating pulse must be retained even while the receiving clock stops.
  @(negedge nes_clk);run_clock=0;
  @(negedge mem_clk);write_byte=1;#1;if(ready)$fatal(1,"write not immediate");checks++;
  @(negedge mem_clk);write_byte=0;repeat(10)@(negedge mem_clk);if(ready)$fatal(1,"stopped clock rearmed");checks++;
  run_clock=1;wait_ready();
  begin_rom();count=19'h60000;loaded=1;run=1;wait_ready();if(epoch!=3||epoch==prior)$fatal(1,"reload epoch");checks++;
  fail=1;#1;if(ready)$fatal(1,"fault not immediate");checks++;fail=0;wait_ready();
  // Accelerate only the2^32-load boundary; do not call this a full loader run.
  @(negedge mem_clk);dut.serial=32'hffffffff;begin_load=1;
  @(negedge mem_clk);begin_load=0;repeat(10)@(negedge nes_clk);
  if(ready||!dut.exhausted)$fatal(1,"epoch wrap admitted");checks++;
  reset=1;repeat(5)@(negedge mem_clk);loaded=0;run=0;reset=0;begin_rom();count=19'h60000;loaded=1;run=1;wait_ready();
  if(epoch!=1)$fatal(1,"reset did not restart epoch");checks++;
  $display("PASS EPOCH205 checks=%0d",checks);$finish;
 end
 initial begin #20000;$fatal(1,"epoch watchdog");end
endmodule
