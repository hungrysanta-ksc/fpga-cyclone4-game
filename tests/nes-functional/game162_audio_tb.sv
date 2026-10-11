// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module audio162_tb;
 reg nc=0,dc=0,reset=1;always #23.280423 nc=~nc;
 parameter real DAC_HALF=5.952381;
 initial begin #1.75;forever #DAC_HALF dc=~dc;end
 reg [15:0] input_sample=16'hffff;
 wire m,l,s,overrun;
 nes_dac162 dut(nc,dc,reset,input_sample,m,l,s,overrun);
 integer n=0,block=0,acc=0,mean=0,dc_est=0,expected=0,packets=0;
 reg old_req=0;reg [15:0] accepted=0;
 // Independent mathematical average/high-pass reference, checked only at
 // published transactions. Integer floor for negative shifts is deliberate.
 always @(negedge nc)if(dut.nr)begin n=0;block=0;acc=0;dc_est=0;old_req=0;end
 else begin
  if(dut.request_toggle!=old_req)begin
   if($signed(dut.held_sample)!==expected)$fatal(1,"filter mismatch got %d exp %d",$signed(dut.held_sample),expected);
   old_req=dut.request_toggle;accepted=dut.held_sample;packets=packets+1;
  end
  if(n==512)begin
   mean=acc/512;expected=((mean*256)-dc_est)>>>8;
   dc_est=dc_est+expected;n=0;acc=0;block=block+1;
  end
  input_sample=16'hffff-((block<3)?0:(block<6?16'h8000:((n&1)?16'h0000:16'hffff)));
  acc=acc+((16'hffff-input_sample)>>1);n=n+1;
 end
 integer transfers=0;reg old_ack=0;
 always @(negedge dc)if(dut.dr)old_ack=0;
 else if(dut.ack_toggle!=old_ack)begin
  if(dut.dac_sample!==accepted)$fatal(1,"torn CDC payload");
  old_ack=dut.ack_toggle;transfers=transfers+1;
 end
 // Board-tested GBC formatter is compiled independently by the runner.
 // The new mono frame latch feeds both reference slots identically.
 wire rm,rl,rs;
 dac_gbc_reference reference(dc,dut.dr,dut.lrck_rising?dut.dac_sample:dut.stereo_sample,rm,rl,rs);
 integer pinchecks=0;
 always @(negedge dc)if(!dut.dr)begin
  if({m,l,s}!=={rm,rl,rs})$fatal(1,"DAC waveform differs from GBC reference");
  pinchecks=pinchecks+1;
 end
 initial begin
  repeat(15)@(negedge nc);reset=0;
  repeat(18000)@(negedge nc);
  if(overrun||packets<30||transfers<30)$fatal(1,"mailbox incomplete/overrun");
  // Async STOP at non-clock boundary must mute and discard pending samples.
  #3.1;reset=1;#100;
  if(s!==0||dut.dac_sample!==0||dut.held_sample!==0)$fatal(1,"STOP not muted");
  input_sample=16'hffff;reset=0;repeat(2000)@(negedge nc);
  if(overrun)$fatal(1,"restart overrun");
  $display("PASS162 AUDIO packets=%0d transfers=%0d pinchecks=%0d",packets,transfers,pinchecks);$finish;
 end
 initial begin #2000000;$fatal(1,"audio watchdog");end
endmodule
