// SPDX-License-Identifier: MIT
// Row verdict joins actual pixel completion. No weakening of whole-frame
// source/row/palette bounds. Wire format is NEW: bits49=raw,52:50=raw slot.
module nes_native_raster181(
 input wire clk,reset,release_packet,begin_packet,end_packet,ppu_ce,source_fault,
 input wire [8:0] scanline,dot,input wire [14:0] scroll_v,scroll_t,
 input wire [2:0] fine_x,pattern_mode,input wire [7:0] display_mask,
 input wire [191:0] palette,input wire scroll_access,
 input wire row_commit,row_patched,input wire [7:0] committed_row,input wire [2:0] row_slot,
 output wire row_needs_patch,
 input wire query,query_palette,input wire [7:0] query_row,
 input wire [4:0] query_bank,query_color,
 output reg owned,valid,scroll_seen,output reg [7:0] errors,row_count,
 output reg [5:0] palette_count,output reg response,hit,output wire [55:0] data
);
 (* ramstyle="M9K" *) reg [55:0] rows[0:223];
 (* ramstyle="M9K" *) reg [7:0] colors[0:63];
 reg active,in_row,row_bad,copy_busy;
 reg [4:0] copy_offset;reg copy_bank;
 reg [191:0] held_palette,line_palette;
 reg [14:0] line_v,line_t;reg [2:0] line_fine,line_mode;
 reg [7:0] line_mask,normal_mask;
 wire line_start=active && ppu_ce && dot==1 && scanline>=8 && scanline<232;
 wire midline=active && in_row && ppu_ce && dot>=2 && dot<=257 && scanline>=8 && scanline<232;
 wire changed=palette_count==0 || line_palette!=held_palette;
 wire [4:0] bank=changed?{4'd0,palette_count[0]}:{4'd0,copy_bank};
 assign row_needs_patch=row_bad;
 reg [55:0] row_q;reg [7:0] color_q;reg palette_q;
 always @(posedge clk)begin
  row_q<=rows[query_row];color_q<=colors[{query_bank[0],query_color}];palette_q<=query_palette;
 end
 assign data=!hit?56'd0:palette_q?{48'd0,color_q}:row_q;
 always @(posedge clk)begin
  response<=0;hit<=0;
  if(reset || release_packet)begin
   owned<=0;valid<=0;active<=0;in_row<=0;row_bad<=0;copy_busy<=0;
   errors<=0;row_count<=0;palette_count<=0;scroll_seen<=0;
   copy_offset<=0;copy_bank<=0;held_palette<=0;line_palette<=0;
   line_v<=0;line_t<=0;line_fine<=0;line_mode<=0;line_mask<=0;normal_mask<=0;
  end else begin
   if(query && owned)begin
    response<=1;
    hit<=valid && (query_palette?({1'b0,query_bank}<palette_count):query_row<224);
   end
   if(begin_packet && !active && !owned)begin
    active<=1;errors<=0;row_count<=0;palette_count<=0;scroll_seen<=0;
    in_row<=0;row_bad<=0;
   end
   if(copy_busy)begin
    colors[{copy_bank,copy_offset}]<={2'b0,held_palette[copy_offset*6+:6]};
    if(copy_offset==31)copy_busy<=0;else copy_offset<=copy_offset+1'b1;
   end
   if(line_start)begin
    if(in_row || scanline!=9'd8+{1'b0,row_count})errors[0]<=1;
    in_row<=1;
    line_v<=scroll_v;line_t<=scroll_t;line_fine<=fine_x;
    line_mode<=pattern_mode;line_mask<=display_mask;line_palette<=palette;
    row_bad<=(display_mask!=8'h18 && display_mask!=8'h1e) ||
      (palette_count!=0 && (display_mask!=normal_mask || palette[5:0]!=held_palette[5:0]));
   end
   if(midline && (palette!=line_palette || fine_x!=line_fine ||
     pattern_mode!=line_mode || display_mask!=line_mask))row_bad<=1;
   if(active && ppu_ce && scanline>=8 && scanline<232 && dot>=1 && dot<=257 && scroll_access)scroll_seen<=1;
   if(active && row_commit)begin
    in_row<=0;
    if(!in_row || committed_row!=row_count || row_count>=224)errors[0]<=1;
    else begin
     row_count<=row_count+1'b1;
     if(row_patched)rows[row_count]<={3'd0,row_slot,1'b1,49'd0};
     else begin
      if(row_bad)errors[3]<=1; // must not bypass a missing raw-row verdict
      rows[row_count]<={7'd0,bank,line_mask,line_mode,line_fine,line_t,line_v};
      if(changed)begin
       if(copy_busy)errors[1]<=1;
       else if(palette_count==2)errors[2]<=1;
       else begin
        held_palette<=line_palette;copy_bank<=bank[0];copy_offset<=0;copy_busy<=1;
        palette_count<=palette_count+1'b1;
        if(palette_count==0)normal_mask<=line_mask;
       end
      end
     end
    end
   end
   if(active && end_packet)begin
    active<=0;owned<=1;
    valid<=errors==0 && row_count==224 && !in_row && !copy_busy && !source_fault;
    if(row_count!=224 || in_row || row_commit)errors[0]<=1;
    if(copy_busy)errors[1]<=1;
   end
   if(source_fault && (active || owned || begin_packet))begin
    active<=0;owned<=1;valid<=0;copy_busy<=0;errors[5]<=1;
   end
  end
 end
endmodule
