// SPDX-License-Identifier: MIT
// Same NES clock as PPU. Sample the settled color/coordinates ONE clock after
// CE, matching the reference post-CE cycle2..257 observation, including stalls.
module nes_patch_capture181(
 input wire clk,reset,release_frame,begin_frame,source_fault,ppu_ce,
 input wire [15:0] generation_in,
 input wire [8:0] scanline,dot,input wire [5:0] color,input wire [2:0] emphasis,
 input wire need_patch,
 input wire query,input wire [15:0] query_generation,
 input wire [2:0] query_slot,input wire [7:0] query_x,
 output wire active,owned,valid,output wire [15:0] generation,
 output wire [7:0] errors,output wire [2:0] count,
 output wire row_commit,row_patched,output wire [7:0] committed_row,
 output wire [2:0] row_slot,output wire response,hit,output wire [5:0] data,
 output wire row_finish
);
 reg ce_after;
 always @(posedge clk)begin
  if(reset || release_frame)ce_after<=0;else ce_after<=ppu_ce;
 end
 wire visible=scanline>=8 && scanline<232;
 wire pixel_valid=ce_after && visible && dot>=2 && dot<=257;
 assign row_finish=ce_after && visible && dot==258;
 wire [8:0] x=dot-9'd2,y=scanline-9'd8;
 nes_patch_rows181 rows(
  .clk(clk),.reset(reset),.release_frame(release_frame),.begin_frame(begin_frame),
  .end_frame(ce_after && scanline==232 && dot==1),
  .source_fault(source_fault || (pixel_valid && emphasis!=0)),
  .generation_in(generation_in),.row_start(ce_after && visible && dot==1),
  .row_end(row_finish),.pixel_valid(pixel_valid),.need_patch(need_patch),
  .row_index(y[7:0]),.pixel_x(x[7:0]),.pixel_color(color),
  .query(query),.query_generation(query_generation),.query_slot(query_slot),.query_x(query_x),
  .active(active),.owned(owned),.valid(valid),.generation(generation),.errors(errors),.count(count),
  .row_commit(row_commit),.row_patched(row_patched),.committed_row(committed_row),.row_slot(row_slot),
  .response(response),.hit(hit),.data(data));
endmodule
