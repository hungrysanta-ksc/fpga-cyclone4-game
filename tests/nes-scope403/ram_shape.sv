// SPDX-License-Identifier: MIT
// Port-shape probe, NOT a capture implementation or a whole-board cost.
module ram_shape403(input wire nes_clk,host_clk,row_we,ctx_we,meta_nwe,meta_hwe,
 input wire[7:0]row_addr,read_addr,input wire[4:0]ctx_addr,
 input wire[55:0]row_data,ctx_data,input wire[9:0]meta_na,meta_ha,
 input wire[7:0]meta_nd,meta_hd,
 output reg[55:0]serialized_q,concurrent_row_q,concurrent_ctx_q,
 output reg[7:0]meta_nq,meta_hq);
 (* ramstyle="M9K, no_rw_check" *)reg[55:0]serialized[0:255];
 (* ramstyle="M9K, no_rw_check" *)reg[55:0]concurrent[0:255];
 (* ramstyle="M9K, no_rw_check" *)reg[7:0]metadata[0:1023];
 wire[7:0]serialized_at=row_we?row_addr:8'd224+ctx_addr;
 always @(posedge nes_clk)begin
  if(row_we||ctx_we)serialized[serialized_at]<=row_we?row_data:ctx_data;
  serialized_q<=serialized[read_addr];
 end
 // Each true-dual-port address serves both its read and write operation.
 always @(posedge nes_clk)begin
  if(row_we)concurrent[row_addr]<=row_data;
  concurrent_row_q<=concurrent[row_addr];
 end
 always @(posedge nes_clk)begin
  if(ctx_we)concurrent[8'd224+ctx_addr]<=ctx_data;
  concurrent_ctx_q<=concurrent[8'd224+ctx_addr];
 end
 always @(posedge nes_clk)begin
  meta_nq<=metadata[meta_na];if(meta_nwe)metadata[meta_na]<=meta_nd;
 end
 always @(posedge host_clk)begin
  meta_hq<=metadata[meta_ha];if(meta_hwe)metadata[meta_ha]<=meta_hd;
 end
endmodule
