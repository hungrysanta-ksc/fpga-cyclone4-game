// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module game161_cache_tb;
 reg clk=0,reset=1;always #23.280 clk=~clk;
 reg cpu_address_valid=0,ppu_address_valid=0,cpumem_read=0,cpu_sample=0;
 reg ppumem_read=0,ppu_sample=0,ppu_prefetch_valid=0;
 reg [24:0] cpumem_addr=25'h3f886;
 reg [21:0] ppumem_addr=22'h3a07f0,ppu_prefetch_address=0;
 reg rom_ready=1,rom_response=0,rom_error=0;
 reg [21:0] rom_response_address=0;reg [7:0] rom_data=0;
 wire [7:0] cpu_data,ppu_data;wire cpu_valid,ppu_valid,rom_request,fault_trigger,fault;
 wire [21:0] rom_address;wire [63:0] fault_context;wire [3:0] error_code;
 wire [11:0] history_flags157;
 nes_rom_early dut(.*);
 integer control=0,cases=0,duplicates=0,i;
 task fresh;
  begin reset=1;cpu_address_valid=0;ppu_address_valid=0;cpumem_read=0;cpu_sample=0;
   ppumem_read=0;ppu_sample=0;ppu_prefetch_valid=0;rom_response=0;rom_error=0;rom_ready=1;ppumem_addr=22'h3a07f0;
   repeat(2)@(negedge clk);reset=0;@(negedge clk);
  end
 endtask
 task fill(input [21:0] addr,input [7:0] value);
  begin ppu_prefetch_address=addr;ppu_prefetch_valid=1;#1;
   if(!rom_request || rom_address!==addr)$fatal(1,"missing legal prefetch %h",addr);
   @(negedge clk);ppu_prefetch_valid=0;rom_ready=0;
   repeat(4)@(negedge clk);
   rom_ready=1;rom_response=1;rom_response_address=addr;rom_data=value;
   @(negedge clk);rom_response=0;
   if(fault)$fatal(1,"fill fault %d",error_code);
  end
 endtask
 initial begin
  if($value$plusargs("CONTROL=%d",control))begin end
  fresh();fill(22'h205ff0,8'ha7);fill(22'h217a18,8'h19);
  // Model the observed local-name-table -> cached205FF0 -> future217FF8 boundary.
  // Cache state is built through accepted replies, never forced internally.
  ppumem_addr=22'h205ff0;ppu_address_valid=1;#1;
  if(!ppu_valid || ppu_data!==8'ha7)$fatal(1,"active byte missing before fill");
  ppu_prefetch_address=22'h217ff8;ppu_prefetch_valid=1;#1;
  if(!rom_request || rom_address!==22'h217ff8)$fatal(1,"future request missing");
  @(negedge clk);rom_ready=0;
  repeat(4)@(negedge clk);
  rom_ready=1;rom_response=1;rom_response_address=22'h217ff8;rom_data=8'hd6;#1;
  duplicates=rom_request;
  if(duplicates!=control || !ppu_valid)$fatal(1,"reply edge duplicate/current mismatch");
  @(negedge clk);rom_response=0;rom_ready=0;ppu_prefetch_valid=0;#1;
  if(ppu_valid===control[0])$fatal(1,"cache eviction mismatch control%0d",control);
  ppu_sample=1;@(negedge clk);ppu_sample=0;
  if(control)begin
   if(!fault || error_code!=2)$fatal(1,"old service did not reproduce error2");
   $display("PASS161 OLD eviction=1 duplicate=1 fault2=1");$finish;
  end
  if(fault || ppu_data!==8'ha7)$fatal(1,"active sample lost");cases++;
  // Repeated future fills must not rotate away the live previous-slot byte.
  rom_ready=1;
  for(i=0;i<8;i=i+1)begin
   fill(22'h217c00+i,8'h40+i);ppu_sample=1;#1;
   if(!ppu_valid || ppu_data!==8'ha7)$fatal(1,"repeated speculation evicted demand");
   @(negedge clk);ppu_sample=0;if(fault)$fatal;cases++;
  end
  // A different future address may be issued on a reply; suppress only same pending address.
  fresh();ppu_prefetch_address=22'h210010;ppu_prefetch_valid=1;@(negedge clk);rom_ready=0;
  repeat(3)@(negedge clk);rom_ready=1;rom_response=1;rom_response_address=22'h210010;rom_data=8'h61;
  ppu_prefetch_address=22'h210018;#1;if(!rom_request || rom_address!==22'h210018)$fatal(1,"different hint blocked");
  @(negedge clk);rom_response=0;rom_ready=0;ppu_prefetch_valid=0;
  repeat(3)@(negedge clk);rom_ready=1;rom_response=1;rom_response_address=22'h210018;rom_data=8'h62;
  @(negedge clk);rom_response=0;ppumem_addr=22'h210010;#1;if(!ppu_valid || ppu_data!==8'h61)$fatal;
  ppumem_addr=22'h210018;#1;if(!ppu_valid || ppu_data!==8'h62)$fatal;cases++;
  // Real demand retains priority and same-cycle reply bypass; reset invalidates both slots.
  fresh();ppumem_addr=22'h205ff0;ppu_address_valid=1;ppu_prefetch_valid=1;ppu_prefetch_address=22'h217ff8;#1;
  if(!rom_request || rom_address!==ppumem_addr)$fatal(1,"prefetch outranked demand");
  @(negedge clk);rom_ready=0;repeat(3)@(negedge clk);
  rom_response=1;rom_response_address=ppumem_addr;rom_data=8'h81;ppu_sample=1;#1;
  if(!ppu_valid || ppu_data!==8'h81 || fault_trigger)$fatal(1,"reply bypass lost");
  @(negedge clk);rom_response=0;ppu_sample=0;if(fault)$fatal;cases++;
  fresh();ppumem_addr=22'h205ff0;#1;if(ppu_valid)$fatal(1,"reset leaked cache");cases++;
  // Existing missing-byte deadline and invalid-response faults are still enforced.
  ppu_sample=1;@(negedge clk);if(!fault || error_code!=2)$fatal;cases++;
  fresh();rom_response=1;@(negedge clk);if(!fault || error_code!=3)$fatal;cases++;
  fresh();cpu_sample=1;@(negedge clk);if(!fault || error_code!=1)$fatal;cases++;
  $display("PASS161 NEW cases=%0d active_byte_preserved duplicate=0 deadlines_retained",cases);$finish;
 end
 initial begin #100000;$fatal(1,"161 watchdog");end
endmodule
