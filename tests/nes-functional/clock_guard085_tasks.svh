// SPDX-License-Identifier: MIT
// Directed traffic enters actual loader/reader inputs, not a pin-level substitute.
// This is fault containment testing; interrupted reads/writes are invalidated.
 integer directed_count=0;
 realtime max_abort=0;
 realtime ce1_start=-1,ce2_start=-1,max_ce_low=0;
 bit deliberate_both_stop=0;
 task automatic measure_ce(input realtime start_time);
  realtime width;
  if(start_time>=0&&!deliberate_both_stop)begin
   width=$realtime-start_time;
   if(width>8000)$fatal(1,"CE_LOW_EXCEEDS_8US");
   if(width>max_ce_low)max_ce_low=width;
  end
 endtask
 always @(negedge psram_1ce)ce1_start=$realtime;
 always @(negedge psram_2ce)ce2_start=$realtime;
 always @(posedge psram_1ce)measure_ce(ce1_start);
 always @(posedge psram_2ce)measure_ce(ce2_start);
 task automatic park_check;
  #40; // model output disable is35ns; not an actual chip/route measurement
  if(!psram_1ce||!psram_2ce||!psram_we||!psram_oe||!psram_bhe||!psram_ble||
     psram_data!==16'hzzzz||mcu_ready||!ram_oe||!ram_we||ram_bus!==8'hzz||nes_run_enable)
   $fatal(1,"FAULT_PINS_NOT_PARKED");
 endtask
 task automatic fresh_session;
  locked=0;clock_enable=1;ref_enable=1;dut.pll.enable=1;#100;
  locked=1;#250000;
  if(!mcu_ready||dut.clock_fault||loaded||loaded_bytes)$fatal(1,"FRESH_SESSION_INVALID");
 endtask
 task automatic begin_traffic(input bit reading);
  if(reading)begin
   force dut.boundary.loader.boot.check_active=1'b1;
   force dut.boundary.loader.boot.reader.check_request=1'b1;
   force dut.boundary.loader.boot.reader.check_address=22'd0;
   @(negedge psram_oe);
  end else begin
   force dut.boundary.loader.boot.load_begin=tb_begin;
   force dut.boundary.loader.boot.load_valid=tb_valid;
   force dut.boundary.loader.boot.load_data=8'ha7;
   @(negedge nes_clk);tb_begin=1;@(negedge nes_clk);tb_begin=0;tb_valid=1;
   @(negedge psram_we);
  end
 endtask
 task automatic end_traffic;
  locked=0;#40;tb_begin=0;tb_valid=0;
  release dut.boundary.loader.boot.load_begin;
  release dut.boundary.loader.boot.load_valid;
  release dut.boundary.loader.boot.load_data;
  release dut.boundary.loader.boot.check_active;
  release dut.boundary.loader.boot.reader.check_request;
  release dut.boundary.loader.boot.reader.check_address;
 endtask
 task automatic directed_clock_faults;
  realtime stopped,latency;
  // No memory clock at startup: a live reference may latch the fault but
  // cannot qualify the missing source. Resuming the source cannot clear it.
  locked=0;clock_enable=0;ref_enable=1;dut.pll.enable=0;#100;locked=1;#10000;
  if(!dut.clock_fault||mcu_ready)$fatal(1,"MISSING_MEMORY_CLOCK_NOT_BLOCKED");
  park_check();clock_enable=1;dut.pll.enable=1;#250000;
  if(!dut.clock_fault||mcu_ready)$fatal(1,"MISSING_MEMORY_CLOCK_REARMED");
  for(integer reading=0;reading<2;reading++)
   for(integer which=0;which<2;which++)
    for(integer phase=0;phase<8;phase++)begin
     fresh_session();begin_traffic(reading!=0);
     #(1+phase*17);stopped=$realtime;
     if(which==0)begin clock_enable=0;dut.pll.enable=0;end
     else ref_enable=0;
     wait(dut.clock_fault===1'b1);
     latency=$realtime-stopped;
     if(latency>5000)$fatal(1,"CLOCK_ABORT_DEADLINE");
     if(latency>max_abort)max_abort=latency;
     park_check();clock_enable=1;ref_enable=1;dut.pll.enable=1;#250000;
     if(!dut.clock_fault||mcu_ready||loaded||loaded_bytes)$fatal(1,"FAULT_NOT_STICKY");
     park_check();directed_count++;end_traffic();
    end
  // Common-cause loss is deliberately NOT fixed by reciprocal monitors.
  fresh_session();begin_traffic(0);#50;deliberate_both_stop=1;
  clock_enable=0;ref_enable=0;dut.pll.enable=0;#9000;
  if(psram_we||(psram_1ce&&psram_2ce)||dut.clock_fault)
   $fatal(1,"BOTH_STOP_COUNTEREXAMPLE_MISSING");
  locked=0;park_check();end_traffic();deliberate_both_stop=0;fresh_session();
  $display("PASS CLOCK085 directed=%0d max_abort_ns=%0.3f both_stop_counterexample=1",directed_count,max_abort);
  $display("PASS CE085 max_low_ns=%0.3f both_stop_excluded=1",max_ce_low);
 endtask
