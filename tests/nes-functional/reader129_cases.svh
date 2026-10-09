// SPDX-License-Identifier: MIT
// Start from seeded READY data; exercise actual CHECK/RUN/reset pin ownership.
for(integer owner=0;owner<2;owner++)
 for(integer phase=0;phase<24;phase++)
  for(integer cause=0;cause<2;cause++)begin
   ready_image129();
   if(!owner)begin
    check_enable=1;wait(check_ready);@(negedge mem_clk);check_address=17;check_request=1;
    @(negedge mem_clk);check_request=0;
   end else begin
    start=1;@(negedge mem_clk);start=0;read_reset=0;
    wait(rom_ready);@(negedge clk);rom_address=17;rom_request=1;
    @(negedge clk);rom_request=0;
   end
   repeat(phase)@(negedge mem_clk);
   if(!cause)reset=1;
   else if(!owner)check_enable=0;
   else read_reset=1;
   #0.001;
   ck(psram_oe&&psram_we&&psram_1ce&&psram_2ce&&!check_response&&!rom_response,"CANCEL129 immediate pins/responses");
   ck(!dut.reader.owner_valid,"CANCEL129 owner cleared");
   repeat(8)@(negedge mem_clk);
   ck(!check_response&&!rom_response,"CANCEL129 no stale response");cancel129++;
  end
// Stop either clock or both while CE is active; a raw reset pulse must cancel
// without a clock edge. Deassertion must wait for each local clock independently.
for(integer clocks=0;clocks<3;clocks++)begin
 ready_image129();check_enable=1;wait(check_ready);
 @(negedge mem_clk);check_address=17;check_request=1;
 @(negedge mem_clk);check_request=0;wait(!psram_oe);#0.010;
 mem_running129=clocks==1;source_running129=clocks==0;
 reset=1;#0.010;
 ck(psram_oe&&psram_1ce&&psram_2ce&&!check_response&&!dut.reader.owner_valid,"STOP129 async cancellation");
 reset=0;check_enable=0;#100;
 if(!mem_running129)ck(dut.reader.mr&&!dut.reader.owner_valid,"STOP129 memory release held");
 if(!source_running129)ck(dut.reader.sr&&!rom_response,"STOP129 source release held");
 mem_running129=1;source_running129=1;repeat(10)@(negedge clk);
 ck(!check_response&&!rom_response&&psram_oe,"STOP129 no replay after restart");stopclock129++;
end
ck(ram.writes==87,"OWNER129 no additional writes from reader tests");
$display("PASS129 reader cancellations=%0d stopped_clock_cases=%0d seeded_images=2",cancel129,stopclock129);
