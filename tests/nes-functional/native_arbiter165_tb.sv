// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module native_arbiter165_tb;
 parameter real PHASE=0.0;
 reg clk=0,mem_clk=0,mem_clock_on=1;always #23.280423 clk=~clk;
 initial begin #(PHASE);forever begin #2.9761905;if(mem_clock_on)mem_clk=~mem_clk;end end
 reg reset=1,slot=0,core_safe=0,core_request=0,fill_request=0,fill_abort=0;
 reg [21:0] core_address=0,fill_address=22'h21efc1;reg [15:0] fill_generation=9;
 wire core_ready,core_response,core_error,fill_ready,fill_idle,fill_response,fill_error,mem_ready,mem_request,mem_response;
 wire [21:0] core_response_address,fill_response_address,mem_address,raw_address;
 wire [7:0] core_data,fill_data,mem_data;wire [15:0] fill_response_generation;
 reg inject_error=0,inject_address=0;wire [21:0] mem_response_address=raw_address^(inject_address?22'd1:22'd0);
 wire mem_error=inject_error;wire fault;
 nes_native_arbiter165 dut(.*);
 wire [21:0] psram_address;wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;wire [15:0] psram_data;
 nes_rom_physical #(.READ_CYCLES(16)) reader(.clk(clk),.mem_clk(mem_clk),.reset(reset),
 .check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),.check_ready(),.check_response(),.check_response_address(),.check_data(),
 .rom_request(mem_request),.rom_address(mem_address),.rom_ready(mem_ready),.rom_response(mem_response),.rom_error(),
 .rom_response_address(raw_address),.rom_data(mem_data),.psram_address(psram_address),.psram_1ce(psram_1ce),.psram_2ce(psram_2ce),
 .psram_oe(psram_oe),.psram_we(psram_we),.psram_bhe(psram_bhe),.psram_ble(psram_ble),.psram_data(psram_data));
 function automatic [7:0] value(input [23:0] a);value=a[7:0]^a[15:8]^a[23:16];endfunction
 wire selected=(!psram_1ce ^ !psram_2ce)&&!psram_oe&&psram_we;
 wire [23:0] base={psram_address,psram_1ce,1'b0};
 assign #70 psram_data=selected?{value(base),value(base+1)}:16'hzzzz;
 integer checks=0,reads=0,maximum=0,n,delay_count;reg [21:0] expected;
 task check(input bit ok,input string why);begin checks++;if(!ok)$fatal(1,"%s",why);end endtask
 task reset_all;
  begin reset=1;fill_abort=0;fill_request=0;core_request=0;inject_error=0;inject_address=0;mem_clock_on=1;
   repeat(4)@(negedge clk);reset=0;wait(mem_ready);@(negedge clk);check(fill_idle&&!fault,"common reset flush");end
 endtask
 task accept_fill;
  begin slot=1;core_safe=1;fill_request=1;wait(fill_ready);@(negedge clk);fill_request=0;check(!fill_idle&&!core_ready,"reader owner retained");end
 endtask
 task finish_fill(input bit aborted);
  begin
   delay_count=0;
   while(!mem_response)begin @(negedge clk);delay_count++;check(delay_count<20,"response bound");end
   if(delay_count+1>maximum)maximum=delay_count+1;
   check(!core_response,"fill must not reach core");
   if(aborted)check(!fill_response,"aborted reply discarded");
   else check(fill_response && fill_response_generation==fill_generation && fill_response_address==fill_address && fill_data===value({2'd0,fill_address}),"tagged physical byte");
   @(negedge clk);check(fill_idle&&!core_response&&!fill_response,"drained exactly once");reads++;
  end
 endtask
 initial begin
  reset_all();fill_request=1;slot=0;core_safe=1;repeat(3)@(negedge clk);check(!mem_request&&!fill_ready,"outside slot denied");
  slot=1;core_safe=0;repeat(3)@(negedge clk);check(!mem_request&&!fill_ready,"core unsafe denied");
  core_safe=1;core_request=1;core_address=22'h001234;
  #1;check(mem_request&&mem_address==core_address&&!fill_ready,"core wins simultaneous request");
  @(negedge clk);core_request=0;slot=0;wait(core_response);@(negedge clk);
  check(core_response_address==core_address&&core_data===value({2'd0,core_address}),"core response unaffected");
  fill_request=0;@(negedge clk);
  for(n=0;n<16;n=n+1)begin fill_address=22'h200000+n;accept_fill();finish_fill(0);check(!fault&&maximum<=7,"physical latency budget");end
  accept_fill();fill_abort=1;repeat(2)@(negedge clk);check(!fill_idle&&!core_response,"abort cannot release live reader");finish_fill(1);fill_abort=0;
  accept_fill();reset_all();repeat(12)@(negedge clk);check(!fill_response&&!core_response,"no old reply after reset");
  // Stop only this test's memory clock: the arbiter must report failure, never
  // declare idle or reset a live shared transaction on its own.
  accept_fill();mem_clock_on=0;repeat(10)@(negedge clk);check(fault&&!fill_idle&&!fill_ready,"lost clock stays owned");
  mem_clock_on=1;wait(mem_response);#1;check(fill_error,"late completion error");repeat(2)@(negedge clk);check(fill_idle,"late completion drains");
  reset_all();inject_error=1;accept_fill();wait(mem_response);repeat(2)@(negedge clk);check(fault,"backend error sticky");
  reset_all();inject_address=1;accept_fill();wait(mem_response);repeat(2)@(negedge clk);check(fault,"wrong address sticky");
  $display("PASS ARBITER165 phase=%0f checks=%0d reads=%0d max=%0d",PHASE,checks,reads,maximum);$finish;
 end
 initial begin #1000000;$fatal(1,"arbiter watchdog");end
endmodule
