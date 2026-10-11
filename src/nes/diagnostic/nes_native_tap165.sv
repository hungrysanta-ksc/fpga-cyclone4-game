// SPDX-License-Identifier: MIT
// Same-edge PPU bus adapter. All ports are in the NES clock domain.
// A read request or an early mapper hint is NOT a received byte.
module nes_native_tap165(
 input wire clk,reset,ppu_ce,ppu_read,ppu_valid,rom_fault,
 input wire [13:0] ppu_logical,
 input wire [21:0] ppu_physical,
 input wire [7:0] ppu_data,
 input wire freeze,release_cache,query,
 input wire [8:0] query_slot,
 input wire [17:0] query_tag,
 input wire [4:0] query_offset,
 input wire query_obj4,
 output wire initialized,owned,response,hit,
 output wire [7:0] data,
 output wire [15:0] valid_bytes
);
 nes_native_chr165 cache(
  .clk(clk),.reset(reset),
  .sample(ppu_ce && ppu_read && !ppu_logical[13]),
  .sample_valid(ppu_valid && !rom_fault),
  .logical_address(ppu_logical[12:0]),.physical_address(ppu_physical),
  .sample_data(ppu_data),.freeze(freeze),.release_cache(release_cache),
  .query(query),.query_slot(query_slot),.query_tag(query_tag),
  .query_offset(query_offset),.query_obj4(query_obj4),
  .initialized(initialized),.owned(owned),.response(response),.hit(hit),
  .data(data),.valid_bytes(valid_bytes));
endmodule
