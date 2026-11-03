// SPDX-License-Identifier: MIT
// Decode a clean START at C2, then vary all live vetoes on its C3 edge.
task start_vetoes572;
 integer mask;
 reg expected;
 for(mask=0;mask<512;mask++)begin
  restart();
  @(negedge mem_clk);#1;
  dut.pending_command=3;old_dut.pending_command=3;
  dut.captured=1;old_dut.captured=1;
  @(negedge mem_clk);#1;
  if(!dut.approved_pulse[3]||!old_dut.approved_pulse[3]||!dut.pending)$fatal(1,"C2 START");
  dut.fault=mask[0];old_dut.fault=mask[0];
  dut.ss_sync[1]=mask[1];old_dut.ss_sync[1]=mask[1];
  check_fault=mask[2];boot_fault=mask[3];
  dut.check_enable=mask[4];old_dut.check_enable=mask[4];
  dut.check_busy=mask[5];old_dut.check_busy=mask[5];
  dut.response_queued471=mask[6];old_dut.response_queued471=mask[6];
  dut.response_low471=mask[7];old_dut.response_low471=mask[7];
  dut.response_high471=mask[8];old_dut.response_high471=mask[8];
  @(posedge mem_clk);#1;
  expected=!mask[0] && mask[1] && !mask[2] && !(mask[3] && mask[4]) &&
           (!mask[6] || (mask[4] && mask[5] && mask[7] && mask[8]));
  if(new_bus[35]!==expected||old_bus[35]!==expected)$fatal(1,"START C3 mask %0d",mask);
  check_fault=0;boot_fault=0;
 end
 $display("PASS572 START 512");
endtask
