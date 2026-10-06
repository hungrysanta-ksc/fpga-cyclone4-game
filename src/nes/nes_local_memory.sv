// SPDX-License-Identifier: MIT
// Original049. One NES master-clock domain. Reset release must be synchronous.
// Hold the core AND packet pipeline in reset until init_done. Every reset clears
// CPU RAM, CIRAM and PRG RAM; this is a diagnostic cold-start policy, not save RAM.
module nes_local_memory(
 input wire clk,reset,
 input wire [24:0] cpumem_addr,input wire cpumem_write,input wire [7:0] cpumem_dout,
 input wire [21:0] ppumem_addr,input wire ppumem_write,input wire [7:0] ppumem_dout,
 input wire [7:0] external_cpu_data,external_ppu_data,
 output wire [7:0] cpumem_din,ppumem_din,output reg init_done
);
 reg [12:0] scrub_address;
 always @(posedge clk or posedge reset)begin
  if(reset)begin scrub_address<=0;init_done<=0;end
  else if(!init_done)begin
   if(scrub_address==13'd8191)init_done<=1;
   else scrub_address<=scrub_address+1'b1;
  end
 end
 wire cpu_selected=cpumem_addr[24:11]==14'h700;
 wire prg_selected=cpumem_addr[24:13]==12'h1e0;
 wire nt_selected=ppumem_addr[21:11]==11'h740;
 wire clearing=!init_done && !reset;
 wire small_clearing=clearing && scrub_address<13'd2048;
 wire [7:0] cpu_q,prg_q,nt_q;
 nes_local_memory_ram #(.AW(11)) cpu_ram(clk,
  !reset && (small_clearing || (init_done && cpumem_write && cpu_selected)),
  init_done?cpumem_addr[10:0]:scrub_address[10:0],init_done?cpumem_dout:8'd0,cpu_q);
 nes_local_memory_ram #(.AW(13)) prg_ram(clk,
  !reset && (clearing || (init_done && cpumem_write && prg_selected)),
  init_done?cpumem_addr[12:0]:scrub_address,init_done?cpumem_dout:8'd0,prg_q);
 nes_local_memory_ram #(.AW(11)) ciram(clk,
  !reset && (small_clearing || (init_done && ppumem_write && nt_selected)),
  init_done?ppumem_addr[10:0]:scrub_address[10:0],init_done?ppumem_dout:8'd0,nt_q);
 assign cpumem_din=(!init_done || reset)?8'd0:cpu_selected?cpu_q:prg_selected?prg_q:external_cpu_data;
 assign ppumem_din=(!init_done || reset)?8'd0:nt_selected?nt_q:external_ppu_data;
endmodule

// Synchronous read-old-data RAM, identical implementation in live RTL and fit.
// No array reset/init statement: explicit address scrub infers FPGA memory.
module nes_local_memory_ram #(parameter AW=11)(
 input wire clk,we,input wire [AW-1:0] address,input wire [7:0] data,output reg [7:0] q
);
 (* ramstyle="M9K" *) reg [7:0] mem[0:(1<<AW)-1];
 always @(posedge clk)begin
  if(we)mem[address]<=data;
  q<=mem[address];
 end
endmodule
