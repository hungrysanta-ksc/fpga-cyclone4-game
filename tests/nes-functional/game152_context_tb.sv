// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module game152_context_tb;
 reg clk=0,reset=1;always #23.280 clk=~clk;
 reg cpu_address_valid=0,ppu_address_valid=0,cpumem_read=0,cpu_sample=0;
 reg ppumem_read=0,ppu_sample=0,ppu_prefetch_valid=0;
 reg [24:0] cpumem_addr=25'h3f887;
 reg [21:0] ppumem_addr=22'h217a19,ppu_prefetch_address=22'h217a18;
 reg rom_ready=1,rom_response=0,rom_error=0;
 reg [21:0] rom_response_address=0;reg [7:0] rom_data=8'h38;
 wire [7:0] cpu_data,ppu_data;wire cpu_valid,ppu_valid,rom_request,fault_trigger,fault;
 wire [21:0] rom_address;wire [63:0] fault_context;wire [3:0] error_code;
 nes_rom_early dut(.*);
 integer cases=0;
 task fresh;
  begin reset=1;cpu_address_valid=0;ppu_address_valid=0;cpumem_read=0;cpu_sample=0;
   ppumem_read=0;ppu_sample=0;ppu_prefetch_valid=0;rom_response=0;rom_error=0;rom_ready=1;
   repeat(2)@(negedge clk);reset=0;@(negedge clk);
  end
 endtask
 initial begin
  // Hardware-like pending PPU age1, but demand differs: do not conflate addresses.
  fresh();ppu_prefetch_valid=1;@(negedge clk);ppu_prefetch_valid=0;rom_ready=0;
  @(negedge clk);ppu_sample=1;#1;
  if(!fault_trigger || !fault_context[63] || fault_context[46:25]!==22'h217a18 ||
     fault_context[24:0]!==25'h217a19 || fault_context[54:47]!==8'd1)$fatal(1,"PPU context mismatch");
  @(negedge clk);if(!fault || error_code!=2)$fatal(1,"PPU deadline suppressed");cases++;
  // Same-demand case remains distinguishable, including a valid zero address byte.
  fresh();ppumem_addr=22'h200000;ppu_address_valid=1;@(negedge clk);rom_ready=0;
  ppu_sample=1;#1;if(fault_context[46:25]!==22'h200000 || fault_context[24:0]!==25'h200000 || !fault_context[63])$fatal;
  @(negedge clk);if(error_code!=2)$fatal;cases++;
  // CPU errors retain the previous25-bit CPU physical-address format.
  fresh();cpu_address_valid=1;@(negedge clk);rom_ready=0;cpu_sample=1;#1;
  if(fault_context[63] || fault_context[24:0]!==cpumem_addr || !fault_trigger)$fatal;
  @(negedge clk);if(error_code!=1)$fatal;cases++;
  // Valid PPU reply at its sample edge must not trigger or poison the cache.
  fresh();ppumem_addr=22'h217a18;ppu_address_valid=1;@(negedge clk);
  rom_response=1;rom_response_address=22'h217a18;ppu_sample=1;#1;
  if(!ppu_valid || ppu_data!==8'h38 || fault_trigger || fault_context[63])$fatal;
  @(negedge clk);rom_response=0;ppu_sample=0;#1;
  if(fault || !ppu_valid || ppu_data!==8'h38)$fatal;cases++;
  // Backend errors still outrank PPU sample failure; top bit is ADDRESS TYPE only.
  fresh();ppu_sample=1;rom_response=1;rom_response_address=22'h217a18;#1;
  if(!fault_context[63] || !fault_trigger)$fatal;
  @(negedge clk);if(error_code!=3)$fatal;cases++;
  fresh();if(fault || fault_trigger)$fatal;cases++;
  $display("PASS GAME152 CONTEXT cases=%0d pending_and_demand_distinct error_priority_preserved",cases);$finish;
 end
 initial begin #20000;$fatal(1,"context watchdog");end
endmodule
