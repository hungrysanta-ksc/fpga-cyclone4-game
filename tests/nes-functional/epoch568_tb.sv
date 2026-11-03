// SPDX-License-Identifier: MIT
`timescale 1ps/1ps
module epoch568_tb;
 reg mem_clk=0,nes_clk=0,run_clock=1,reset=0,load_begin=0,load_valid=0;
 reg loaded=0,run_enable=0,loader_fault=0;
 wire local_reset,source_ready,source_is_rom,source_writing;wire [31:0] live_epoch;
 wire [18:0] loaded_bytes=loaded?19'h60000:19'd0;
 always #2976 mem_clk=!mem_clk;
 always #23281 if(run_clock)nes_clk=!nes_clk;
 nes_domain_reset124 core_release(nes_clk,reset||!run_enable,local_reset);
 nes_source_epoch207 dut(.*);
 reg [31:0] previous_serial,next_serial,want;
 bit monitor=0;
 always @(negedge nes_clk)if(monitor&&source_ready&&(live_epoch!==want||!source_is_rom||source_writing))
  $fatal(1,"admitted stale epoch");
 initial begin
  for(int i=0;i<32;i++)for(int p=0;p<2;p++)begin
   @(negedge nes_clk);monitor=0;run_enable=0;loaded=0;reset=1;
   #100;if(source_ready)$fatal(1,"reset mask");
   repeat(3)@(negedge mem_clk);reset=0;
   previous_serial=(32'd1<<i)-1;next_serial=previous_serial+1;
   dut.serial=previous_serial;dut.gray=previous_serial^(previous_serial>>1);
   if(p)run_clock=0;
   @(negedge mem_clk);load_begin=1;@(negedge mem_clk);load_begin=0;
   if(!dut.gray_pending||source_ready)$fatal(1,"pending publish");
   @(negedge mem_clk);want=next_serial^(next_serial>>1);
   if(dut.gray!==want||((previous_serial^(previous_serial>>1))^want)!==(32'd1<<i))$fatal(1,"wrong Gray transition");
   monitor=1;run_enable=1;loaded=1;
   if(p)begin repeat(13)@(negedge mem_clk);if(source_ready)$fatal(1,"stopped");run_clock=1;end
   repeat(12)@(negedge nes_clk);if(!source_ready||live_epoch!==want)$fatal(1,"missing epoch");
   loader_fault=1;#100;if(source_ready||source_is_rom||!source_writing)$fatal(1,"fault mask");
   loader_fault=0;
  end
  $display("PASS568 epoch=64");$finish;
 end
 initial begin #200000000;$fatal(1,"timeout");end
endmodule
