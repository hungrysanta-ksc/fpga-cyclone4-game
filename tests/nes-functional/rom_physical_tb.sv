// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module rom_physical_tb;
 reg clk=0,mem_clk=0,reset=1,mem_run=1;
 always #23.280423 clk=~clk;
 integer phase_ps,unused;initial begin unused=$value$plusargs("PHASE_PS=%d",phase_ps);#(phase_ps/1000.0);forever begin #5.952381;if(mem_run)mem_clk=~mem_clk;end end
 reg rom_request=0;reg [21:0] rom_address=0;
 wire rom_ready,rom_response,rom_error;wire [21:0] rom_response_address;wire [7:0] rom_data;
 wire [21:0] psram_address;wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;wire [15:0] psram_data;
 nes_rom_physical dut(.*);
`ifdef LATE_MEMORY
 rom_physical_model #(.ACCESS_NS(60.0)) memory(.*);
`else
 rom_physical_model memory(.*);
`endif
 integer accepted=0,completed=0,canceled=0,checks=0,ticks=0,start_tick=0,min_ticks=1000,max_ticks=0,pin_reads=0;
 integer pin_cycles=0,idle_cycles=0;
 reg pending=0;reg [21:0] expected_address;reg [21:0] last_pin_address;reg last_chip;reg pin_active=0;
 function automatic [7:0] expected(input [21:0] a);expected=a[7:0]^a[15:8]^{a[19:16],2'b0,a[21:20]}^8'hb7;endfunction
 task automatic check(input bit ok);if(!ok)$fatal(1,"PHYSICAL check%0d accept%0d complete%0d addr%h got%h",checks,accepted,completed,expected_address,rom_data);checks++;endtask
 always @(posedge reset)begin if(pending)canceled++;pending=0;pin_active=0;end
 always @(posedge clk)begin
  ticks++;
  if(!reset)begin
   if(rom_response)begin
    check(pending && !rom_error && rom_response_address===expected_address && rom_data===expected(expected_address));
    if(ticks-start_tick<min_ticks)min_ticks=ticks-start_tick;
    if(ticks-start_tick>max_ticks)max_ticks=ticks-start_tick;
    pending=0;completed++;
   end
   if(rom_request && rom_ready)begin check(!pending);pending=1;expected_address=rom_address;accepted++;start_tick=ticks;end
  end
 end
 always @(negedge mem_clk)begin
  check(psram_we && !(~psram_1ce && ~psram_2ce));
  if(!reset && !psram_oe)begin
   if(!pin_active)begin
    check(idle_cycles>=1);pin_cycles=0;idle_cycles=0;
    check(pending && {psram_address,psram_1ce,1'b0}=={2'b0,expected_address[21:1],1'b0});
    pin_reads++;last_pin_address=psram_address;last_chip=psram_1ce;
   end else check(psram_address==last_pin_address && psram_1ce==last_chip);
   pin_cycles++;pin_active=1;
  end else begin
   if(pin_active && !reset)check(pin_cycles==3);
   pin_active=0;idle_cycles++;
  end
 end
 task automatic restart;
  #3.123;reset=1;rom_request=0;#1;check(psram_oe && psram_1ce && psram_2ce && !rom_ready && !rom_response);
  repeat(3)@(negedge clk);reset=0;wait(rom_ready);
 endtask
 task automatic issue(input [21:0] address);
  @(negedge clk);wait(rom_ready);rom_address=address;rom_request=1;
  @(negedge clk);rom_request=0;rom_address=~address;
 endtask
 initial begin
  #100;reset=0;wait(rom_ready);
  // Continuous ready-qualified grants exercise simultaneous response/new request.
  for(integer k=0;k<512;k++)begin
   @(negedge clk);while(!rom_ready)@(negedge clk);
   rom_request=1;rom_address=(k*22'h163b1) & 22'h3fffff;
   @(negedge clk);rom_request=0;rom_address=~rom_address;
  end
  wait(!pending);repeat(5)@(negedge clk);check(completed==512);
  // Cancel before crossing, during the pin read, and while return ack propagates.
  for(integer k=0;k<12;k++)begin
   issue(22'h200010+k);#(k*9.0);restart();repeat(6)@(negedge clk);check(!pending && !rom_response);
   issue(22'h101+k);wait(!pending);
  end
  // A stopped memory clock must neither fabricate a response nor retain a
  // pre-reset completion when the clock is restarted.
  @(negedge mem_clk);mem_run=0;issue(22'h123456);repeat(12)@(negedge clk);check(pending && !rom_ready && !rom_response);
  restart();repeat(4)@(negedge clk);mem_run=1;repeat(8)@(negedge clk);check(!rom_response);
  issue(22'h234567);wait(!pending);repeat(5)@(negedge clk);
  check(accepted==completed+canceled && canceled>0 && completed==525);
  $display("PASS PHYSICAL checks=%0d accepted=%0d completed=%0d canceled=%0d pins=%0d latency=%0d..%0d phase_ps=%0d",checks,accepted,completed,canceled,pin_reads,min_ticks,max_ticks,phase_ps);$finish;
 end
 initial begin #1000000;$fatal(1,"watchdog");end
endmodule
