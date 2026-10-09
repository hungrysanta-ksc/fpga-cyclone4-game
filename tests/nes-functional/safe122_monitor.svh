// SPDX-License-Identifier: MIT
// Candidate122 only: 1ps-quantized168MHz control,16 active cycles before sample.
// Digital setup/hold monitors; not board pad/PCB or post-fit timing signoff.
realtime address_changed122=0,active_started122=0,sampled122=0;
reg sample_seen122=0;
integer setup_checks122=0,hold_checks122=0;
always @(psram_address) address_changed122=$realtime;
always @(posedge reset) sample_seen122=0;
always @(negedge psram_oe) if(!reset)begin
 check($realtime-address_changed122>=5.951);
 active_started122=$realtime;sample_seen122=0;setup_checks122++;
end
always @(posedge mem_clk) if(!reset && dut.state==dut.ACTIVE && dut.remaining==1)begin
 check(!psram_oe && $realtime-active_started122>=95.231);
 sampled122=$realtime;sample_seen122=1;
end
always @(posedge psram_oe) if(!reset && sample_seen122)begin
 if($realtime-sampled122<5.951)$fatal(1,"SAFE122 hold interval");
 check($realtime-sampled122>=5.951);
 check($realtime-active_started122>=101.183);
 sample_seen122=0;hold_checks122++;
end
always @(posedge clk) if(!reset && rom_response)
 check(psram_oe && psram_1ce && psram_2ce);
