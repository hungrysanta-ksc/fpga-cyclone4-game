// SPDX-License-Identifier: MIT
// Bounded, already-composited PPU rows. NOT connected to the game path yet.
// Caller supplies aligned final pixels, marks any row that cannot be described
// by native tiles, and copies row_commit/row_slot into its own row descriptor.
// Seven retained rows plus one scratch row; no payload reset or external SRAM.
module nes_patch_rows181(
 input wire clk,reset,release_frame,begin_frame,end_frame,source_fault,
 input wire [15:0] generation_in,
 input wire row_start,row_end,pixel_valid,need_patch,
 input wire [7:0] row_index,pixel_x,input wire [5:0] pixel_color,
 input wire query,input wire [15:0] query_generation,
 input wire [2:0] query_slot,input wire [7:0] query_x,
 output reg active,owned,valid,output reg [15:0] generation,
 output reg [7:0] errors,output reg [2:0] count,
 output reg row_commit,row_patched,output reg [7:0] committed_row,
 output reg [2:0] row_slot,
 output reg response,hit,output wire [5:0] data
);
 (* ramstyle="M9K" *) reg [5:0] pixels[0:2047];
 reg [5:0] pixel_q;
 reg in_row,patch;reg [8:0] next_x;reg [7:0] next_row;
 wire row_ok=active && in_row && row_index==next_row;
 wire write_pixel=row_ok && pixel_valid && next_x<256 && pixel_x==next_x[7:0];
 wire final_patch=patch || need_patch;
 wire query_ok=query && owned && valid && generation==query_generation && query_slot<count && !release_frame && !reset && !source_fault;
 // BRAM payload is never reset and can only be read through a sealed lease.
 always @(posedge clk)begin
  pixel_q<=pixels[{query_slot,query_x}];
  if(!reset && !release_frame && !source_fault && write_pixel)
   pixels[{count,pixel_x}]<=pixel_color;
 end
 assign data=hit?pixel_q:6'd0;
 always @(posedge clk)begin
  response<=0;hit<=0;row_commit<=0;
  if(reset || release_frame)begin
   active<=0;owned<=0;valid<=0;generation<=0;errors<=0;count<=0;
   in_row<=0;patch<=0;next_x<=0;next_row<=0;row_patched<=0;committed_row<=0;row_slot<=0;
  end else begin
   if(query)begin response<=1;hit<=query_ok;end
   if(begin_frame && !active && !owned)begin
    active<=1;valid<=0;generation<=generation_in;errors<=0;count<=0;
    in_row<=0;next_x<=0;next_row<=0;patch<=0;
   end
   if(active)begin
    if(row_start)begin
     if(in_row || row_index!=next_row || next_row>=224 || pixel_valid || row_end)errors[0]<=1;
     else begin in_row<=1;next_x<=0;patch<=need_patch;end
    end
    if(in_row && need_patch)patch<=1;
    if(pixel_valid)begin
     if(!write_pixel || row_start || row_end)errors[1]<=1;
     else next_x<=next_x+1'b1;
    end
    if(row_end)begin
     in_row<=0;
     if(!row_ok || next_x!=256 || pixel_valid || row_start)errors[2]<=1;
     else begin
      next_row<=next_row+1'b1;
      row_commit<=1;committed_row<=next_row;row_patched<=final_patch;row_slot<=count;
      if(final_patch)begin
       if(count==7)errors[3]<=1;
       else count<=count+1'b1;
      end
     end
    end
    // Independent cycle after the final row_commit. A stopped PPU source may
    // retire immediately through source_fault without awaiting another pixel.
    if(end_frame)begin
     active<=0;owned<=1;
     valid<=errors==0 && next_row==224 && !in_row && !row_start && !row_end && !pixel_valid && !source_fault;
     if(next_row!=224 || in_row || row_start || row_end || pixel_valid)errors[4]<=1;
    end
   end
   if(source_fault && (active || owned || begin_frame))begin
    active<=0;owned<=1;valid<=0;in_row<=0;errors[5]<=1;
   end
  end
 end
endmodule
