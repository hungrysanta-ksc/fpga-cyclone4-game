// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module rom_service_tb;
 reg clk=0,reset=1;always #5 clk=~clk;
 reg [24:0] cpumem_addr=0;reg cpumem_read=0,cpu_sample=0;
 reg [21:0] ppumem_addr=22'h200000;reg ppumem_read=0,ppu_sample=0;
 wire [7:0] cpu_data,ppu_data;wire cpu_valid,ppu_valid;
 reg rom_ready=1,rom_response=0,rom_error=0;wire rom_request;wire [21:0] rom_address;
 reg [21:0] rom_response_address=0;reg [7:0] rom_data=0;
 wire fault;wire [3:0] error_code;
 nes_rom_service dut(.*);
 integer checks=0,requests=0,negative_cases=0;
 always @(posedge clk)if(rom_request)requests++;
 task automatic tick;@(posedge clk);#1;endtask
 task automatic check(input bit ok);if(!ok)$fatal(1,"check%0d code%0d cpu%h ppu%h",checks,error_code,cpumem_addr,ppumem_addr);checks++;endtask
 task automatic clean;
  @(negedge clk);reset=1;rom_response=0;rom_error=0;cpumem_read=0;ppumem_read=0;cpu_sample=0;ppu_sample=0;rom_ready=1;
  tick();check(!rom_request && !cpu_valid && !ppu_valid && !fault);
  @(negedge clk);reset=0;
 endtask
 task automatic failcase(input integer code);
  tick();check(fault && error_code==code);negative_cases++;
  @(negedge clk);rom_response=0;rom_error=0;cpu_sample=0;ppu_sample=0;cpumem_read=1;ppumem_read=1;
  repeat(3)begin tick();check(!rom_request && fault && error_code==code);end
 endtask
 task automatic fetch(input bit isppu,input [21:0] address,input [7:0] value);
  integer prior_requests;
  @(negedge clk);cpu_sample=0;ppu_sample=0;cpumem_read=!isppu;ppumem_read=isppu;
  if(isppu)ppumem_addr=address;else cpumem_addr={3'b0,address};
  prior_requests=requests;#1;check(rom_request && rom_address==address);tick();check(requests==prior_requests+1);
  @(negedge clk);rom_response=1;rom_response_address=address;rom_data=value;
  cpu_sample=!isppu;ppu_sample=isppu;#1;
  check(isppu?(ppu_valid && ppu_data==value):(cpu_valid && cpu_data==value));
  tick();check(!fault);
  @(negedge clk);rom_response=0;
  repeat(3)begin tick();check(!rom_request && !fault && (isppu?(ppu_valid && ppu_data==value):(cpu_valid && cpu_data==value)));end
  check(requests==prior_requests+1);
 endtask
 initial begin
  tick();clean();
  for(integer k=0;k<256;k++)begin fetch(0,(k*251+13)&65535,k^8'ha7);fetch(1,22'h200000|((k*127+9)&32767),k^8'h5c);end
  clean();
  // Simultaneous miss: PPU first; response and CPU grant on the same edge.
  cpumem_addr=25'h1234;ppumem_addr=22'h205678;cpumem_read=1;ppumem_read=1;
  #1;check(rom_request && rom_address==22'h205678);tick();
  @(negedge clk);rom_response=1;rom_response_address=22'h205678;rom_data=8'hac;ppu_sample=1;
  #1;check(ppu_valid && ppu_data==8'hac && rom_request && rom_address==22'h1234);tick();check(!fault);
  @(negedge clk);rom_response_address=22'h1234;rom_data=8'h37;cpu_sample=1;
  #1;check(cpu_valid && cpu_data==8'h37 && ppu_valid && ppu_data==8'hac);tick();check(!fault);
  @(negedge clk);rom_response=0;tick();check(cpu_valid && ppu_valid && !rom_request);
  clean();
  // Backend unavailable: no grant; live request address may change prior_requests grant.
  rom_ready=0;cpumem_addr=25'h111;cpumem_read=1;repeat(7)begin tick();check(!rom_request && !fault);end
  @(negedge clk);cpumem_addr=25'h222;rom_ready=1;#1;check(rom_request && rom_address==22'h222);tick();
  // Common reset discards outstanding and both cache tags. Backend must flush too.
  clean();check(!cpu_valid && !ppu_valid);
  // Non-ROM address deadlines do not request or fault.
  cpumem_addr=25'h380000;ppumem_addr=22'h3a0000;cpumem_read=1;ppumem_read=1;cpu_sample=1;ppu_sample=1;
  tick();check(!fault && !rom_request);clean();
  cpumem_addr=25'h444;cpu_sample=1;failcase(1);clean();
  ppumem_addr=22'h200555;ppu_sample=1;failcase(2);clean();
  rom_response=1;failcase(3);clean();
  cpumem_addr=25'h100;cpumem_read=1;tick();@(negedge clk);rom_response=1;rom_response_address=22'h101;failcase(4);clean();
  cpumem_addr=25'h100;cpumem_read=1;tick();@(negedge clk);rom_response=1;rom_response_address=22'h100;rom_error=1;failcase(5);clean();
  cpumem_addr=25'h100;cpumem_read=1;tick();repeat(255)tick();check(!fault);failcase(6);clean();
  $display("PASS ROM SERVICE checks=%0d requests=%0d cache_pairs=256 negative_cases=%0d",checks,requests,negative_cases);$finish;
 end
 initial begin #1000000;$fatal(1,"watchdog");end
endmodule
