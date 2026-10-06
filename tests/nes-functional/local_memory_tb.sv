// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module local_memory_tb;
 reg clk=0,reset=1;always #5 clk=~clk;
 reg [24:0] cpumem_addr=0;reg cpumem_write=0;reg [7:0] cpumem_dout=0;
 reg [21:0] ppumem_addr=0;reg ppumem_write=0;reg [7:0] ppumem_dout=0;
 reg [7:0] external_cpu_data=8'hc5,external_ppu_data=8'h39;
 wire [7:0] cpumem_din,ppumem_din;wire init_done;
 nes_local_memory dut(.*);
 integer checks=0,scrubs=0;
 task automatic tick;@(posedge clk);#1;endtask
 task automatic eq(input [7:0] a,b);if(a!==b)$fatal(1,"data %h != %h cpu%h ppu%h",a,b,cpumem_addr,ppumem_addr);checks++;endtask
 task automatic scrub;
  @(negedge clk);reset=0;
  for(integer k=0;k<8192;k++)begin
   tick();if(init_done!==(k==8191))$fatal(1,"scrub length at%0d",k);
   if(k<8191)begin eq(cpumem_din,0);eq(ppumem_din,0);end
  end
  scrubs++;
 endtask
 task automatic scan_zero;
  for(integer k=0;k<8192;k++)begin
   @(negedge clk);cpumem_addr=25'h3c0000+k;ppumem_addr=22'h3a0000+(k%2048);tick();eq(cpumem_din,0);eq(ppumem_din,0);
   if(k<2048)begin @(negedge clk);cpumem_addr=25'h380000+k;tick();eq(cpumem_din,0);end
  end
 endtask
 initial begin
  tick();scrub();scan_zero();
  // Every address, old-data read during write, then read back. CPU/CIRAM concurrent.
  for(integer k=0;k<8192;k++)begin
   @(negedge clk);cpumem_addr=25'h3c0000+k;cpumem_dout=(k^8'ha7);cpumem_write=1;
   ppumem_addr=22'h3a0000+(k%2048);ppumem_dout=(k^8'h5c);ppumem_write=k<2048;
   tick();eq(cpumem_din,0);if(k<2048)eq(ppumem_din,0);
   @(negedge clk);cpumem_write=0;ppumem_write=0;tick();eq(cpumem_din,(k^8'ha7));eq(ppumem_din,(k^8'h5c));
  end
  for(integer k=0;k<2048;k++)begin
   @(negedge clk);cpumem_addr=25'h380000+k;cpumem_dout=k^8'hd3;cpumem_write=1;tick();eq(cpumem_din,0);
   @(negedge clk);cpumem_write=0;tick();eq(cpumem_din,k^8'hd3);
  end
  // Decode boundaries must fall back to external data, not alias local RAM.
  for(integer k=0;k<4;k++)begin
   @(negedge clk);case(k)
    0:begin cpumem_addr=25'h37ffff;ppumem_addr=22'h39ffff;end
    1:begin cpumem_addr=25'h380800;ppumem_addr=22'h3a0800;end
    2:begin cpumem_addr=25'h3bffff;ppumem_addr=22'h200000;end
    3:begin cpumem_addr=25'h3c2000;ppumem_addr=22'h3fffff;end
   endcase
   cpumem_write=1;ppumem_write=1;tick();eq(cpumem_din,8'hc5);eq(ppumem_din,8'h39);
  end
  // Full readback detects decoder aliasing and corruption of earlier addresses.
  for(integer k=0;k<8192;k++)begin
   @(negedge clk);cpumem_write=0;ppumem_write=0;
   cpumem_addr=25'h3c0000+k;ppumem_addr=22'h3a0000+(k%2048);
   tick();eq(cpumem_din,k^8'ha7);eq(ppumem_din,k^8'h5c);
   if(k<2048)begin @(negedge clk);cpumem_addr=25'h380000+k;tick();eq(cpumem_din,k^8'hd3);end
  end
  @(negedge clk);cpumem_write=1;ppumem_write=1;
  // Asynchronous assertion masks outputs immediately and wins a pending write.
  @(negedge clk);cpumem_addr=25'h380000;ppumem_addr=22'h3a0000;
  #2;reset=1;#1;if(init_done)$fatal(1,"reset admission");eq(cpumem_din,0);eq(ppumem_din,0);tick();
  // Caller writes stay asserted throughout scrub; they may not defeat clearing.
  scrub();@(negedge clk);cpumem_write=0;ppumem_write=0;scan_zero();
  @(negedge clk);reset=1;tick();@(negedge clk);reset=0;repeat(123)tick();
  @(negedge clk);reset=1;tick();scrub();scan_zero();
  $display("PASS LOCAL MEMORY checks=%0d complete_scrubs=%0d interrupted_scrubs=1 bytes=12288",checks,scrubs);$finish;
 end
 initial begin #2000000;$fatal(1,"watchdog");end
endmodule
