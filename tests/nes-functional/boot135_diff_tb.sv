// SPDX-License-Identifier: MIT
// Exhaustive clocked next-state comparison of the exact sticky ownership latch.
// Loader/reader outputs are controlled here; this is not a PSRAM transfer test.
`timescale 1ns/1ps
module boot135_diff_tb;
 reg clk=0,mem_clk=0,reset=1,read_reset=1;
 reg check_enable=0,check_request=0,load_begin=0,load_chr32=0,load_valid=0,load_end=0,start=0,stop=0,rom_request=0;
 reg [16:0] check_address=0;reg [7:0] load_data=0;reg [21:0] rom_address=0;
 reg in_run=0,in_loaded=0,in_fault=0,in_ready=0,in_address=0;
 nes_rom_boot dut(.clk(clk),.mem_clk(mem_clk),.reset(reset),.read_reset(read_reset),
  .check_enable(check_enable),.check_request(check_request),.check_address(check_address),
  .load_begin(load_begin),.load_chr32(load_chr32),.load_valid(load_valid),.load_end(load_end),.start(start),.stop(stop),.load_data(load_data),
  .rom_request(rom_request),.rom_address(rom_address));
 baseline_boot135 refdut(.clk(clk),.mem_clk(mem_clk),.reset(reset),.read_reset(read_reset),
  .check_enable(check_enable),.check_request(check_request),.check_address(check_address),
  .load_begin(load_begin),.load_chr32(load_chr32),.load_valid(load_valid),.load_end(load_end),.start(start),.stop(stop),.load_data(load_data),
  .rom_request(rom_request),.rom_address(rom_address));
 integer cases=0;
 initial begin
  force dut.loader_run=in_run;force refdut.loader_run=in_run;
  force dut.loaded=in_loaded;force refdut.loaded=in_loaded;
  force dut.boot_fault=in_fault;force refdut.boot_fault=in_fault;
  force dut.raw_check_ready=in_ready;force refdut.raw_check_ready=in_ready;
  force dut.address_valid=in_address;force refdut.address_valid=in_address;
  #1;mem_clk=1;#1;mem_clk=0;reset=0;
  for(integer flags=0;flags<4096;flags++)begin
   dut.check_failed=flags[0];refdut.check_failed=flags[0];
   check_enable=flags[1];check_request=flags[2];load_begin=flags[3];load_valid=flags[4];load_end=flags[5];start=flags[6];
   in_run=flags[7];in_loaded=flags[8];in_fault=flags[9];in_ready=flags[10];in_address=flags[11];
   #1;mem_clk=1;#1;
   if(dut.check_failed!==refdut.check_failed)$fatal(1,"BOOT135 mismatch flags=%h new=%b old=%b",flags,dut.check_failed,refdut.check_failed);
   mem_clk=0;cases++;
  end
  reset=1;#0.001;if(dut.check_failed!==0)$fatal(1,"BOOT135 reset");
  $display("PASS135 boot sticky equivalence cases=%0d",cases);$finish;
 end
endmodule
