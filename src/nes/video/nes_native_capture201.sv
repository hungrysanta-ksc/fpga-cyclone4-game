// SPDX-License-Identifier: MIT
// Candidate board join: actual capture + retained source ownership.
// release_frame is the exporter request; effective_release clears shared users.
module nes_native_capture201(
 input wire source_ready,source_is_rom,source_writing,input wire [31:0] live_epoch,
 input wire [3:0] export_error,input wire reader_drained,retire_commit,
 input wire [15:0] retire_generation,
 output wire effective_release,lease_valid,retire_permitted,export_permitted,waiting_display,lease_fault,
 output wire [31:0] captured_epoch,output wire [15:0] captured_generation,
 input wire clk,reset,release_frame,ppu_ce,rom_fault,
 input wire [8:0] scanline,dot,input wire [5:0] color,input wire [2:0] emphasis,
 input wire bg_low,bg_high,obj_low,obj_high,obj_valid,extra_sprites,
 input wire [1:0] bg_attribute,input wire [7:0] obj_attribute,obj_x,
 input wire ppu_read,ppu_valid,input wire [13:0] logical_address,input wire [21:0] physical_address,
 input wire [14:0] scroll_v,scroll_t,input wire [2:0] fine_x,pattern_mode,
 input wire [7:0] display_mask,input wire [191:0] palette,input wire scroll_access,
 input wire query,input wire [2:0] query_kind,input wire [12:0] query_index,input wire [15:0] query_generation,
 output wire capture_begin,output wire owned,geometry_valid,output wire initialized,active,output wire [15:0] generation,
 output wire [24:0] errors,output wire [24:0] observe_errors180,
 output wire observe_collecting180,output wire scroll_seen,
 output wire [7:0] row_count,object_count,exception_count,output wire [5:0] group_count,palette_count,
 output wire response,output wire hit,output wire [63:0] data,
 output wire [7:0] patch_errors,output wire [2:0] patch_count
);
 nes_native_frame201 frame(.release_frame(effective_release),.rom_fault(rom_fault||lease_fault),.*);
 nes_capture_lease201 ownership(
  .clk(clk),.reset(reset),.stop(1'b0),.capture_begin(capture_begin),
  .frame_owned(owned),.geometry_valid(geometry_valid),.frame_generation(generation),
  .export_release(release_frame),.export_error(export_error),
  .source_ready(source_ready),.source_is_rom(source_is_rom),.source_writing(source_writing),.live_epoch(live_epoch),
  .reader_drained(reader_drained),.retire_commit(retire_commit),.retire_generation(retire_generation),
  .release_frame(effective_release),.lease_valid(lease_valid),.retire_permitted(retire_permitted),.export_permitted(export_permitted),
  .captured_epoch(captured_epoch),.captured_generation(captured_generation),.waiting_display(waiting_display),.fault(lease_fault));
endmodule
