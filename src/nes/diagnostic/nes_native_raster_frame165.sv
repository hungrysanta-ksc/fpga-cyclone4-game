// SPDX-License-Identifier: MIT
// NES-clock-only state packet. This does NOT certify complete CHR/map/OAM data.
module nes_native_raster_frame165(
 output reg scroll_seen,
 input wire clk,reset,ppu_ce,
 input wire [8:0] scanline,dot,
 input wire [14:0] scroll_v,scroll_t,
 input wire [2:0] fine_x,pattern_mode,
 input wire [7:0] display_mask,
 input wire [191:0] palette,
 input wire scroll_access,source_fault,
 input wire release_packet,query,query_palette,
 input wire [7:0] query_row,
 input wire [4:0] query_bank,query_color,
 output reg owned,valid,
 output reg [15:0] generation,
 output reg [7:0] errors,row_count,
 output reg [5:0] palette_count,
 output reg response,hit,
 output reg [55:0] data
);
 // Row: v[14:0], t[29:15], x[32:30], mode[35:33], mask[43:36],
 // palette bank[48:44], reserved zero[55:49]. v/t are RAW Loopy state.
 reg [55:0] rows[0:223];
 reg [7:0] colors[0:1023];
 reg active,copy_busy;
 reg [4:0] copy_offset,copy_bank;
 reg [191:0] held_palette,line_palette;
 reg [2:0] line_fine,line_mode;
 reg [7:0] line_mask;
 wire line_start=ppu_ce && dot==1 && scanline>=8 && scanline<232;
 wire begin_packet=line_start && scanline==8 && !owned && !active;
 wire row_event=line_start && (active || begin_packet);
 wire changed=begin_packet || palette!=line_palette;
 wire [4:0] row_bank=begin_packet?5'd0:changed?palette_count[4:0]:copy_bank;
 wire midline=active && ppu_ce && scanline>=8 && scanline<232 && dot>=2 && dot<=256;
 always @(posedge clk) begin
  response<=0;hit<=0;data<=0;
  if(reset) begin
   owned<=0;valid<=0;active<=0;copy_busy<=0;generation<=0;
   errors<=0;row_count<=0;palette_count<=0;scroll_seen<=0;copy_offset<=0;copy_bank<=0;
   held_palette<=0;line_palette<=0;line_fine<=0;line_mode<=0;line_mask<=0;
  end else if(release_packet) begin
   owned<=0;valid<=0;active<=0;copy_busy<=0;
   errors<=0;row_count<=0;palette_count<=0;scroll_seen<=0;
  end else begin
   if(query && owned) begin
    response<=1;
    if(valid && (query_palette ? ({1'b0,query_bank}<palette_count) : query_row<224)) begin
     hit<=1;
     data<=query_palette?{48'd0,colors[{query_bank,query_color}]}:rows[query_row];
    end
   end
   if(copy_busy) begin
    colors[{copy_bank,copy_offset}]<={2'b00,held_palette[copy_offset*6+:6]};
    if(copy_offset==31)copy_busy<=0;
    else copy_offset<=copy_offset+1'b1;
   end
   if(begin_packet) begin
    active<=1;valid<=0;generation<=generation+1'b1;errors<=0;
    row_count<=0;palette_count<=0;
   end
   if(row_event) begin
    if(display_mask!=8'h1e)errors[6]<=1;
    if(!begin_packet && palette[5:0]!=held_palette[5:0])errors[7]<=1;
    // A skipped/repeated row cannot leave stale RAM in a publishable packet.
    if(!begin_packet && scanline!=9'd8+{1'b0,row_count})errors[0]<=1;
    if(row_count<224 || begin_packet) begin
     rows[scanline-9'd8]<={7'd0,row_bank,display_mask,pattern_mode,fine_x,scroll_t,scroll_v};
     row_count<=begin_packet?8'd1:row_count+1'b1;
    end else errors[0]<=1;
    line_palette<=palette;line_fine<=fine_x;line_mode<=pattern_mode;line_mask<=display_mask;
    if(changed) begin
     if(copy_busy)errors[1]<=1;
     else if(!begin_packet && palette_count==2)errors[2]<=1;
     else begin
      held_palette<=palette;copy_bank<=row_bank;copy_offset<=0;copy_busy<=1;
      palette_count<=begin_packet?6'd1:palette_count+1'b1;
     end
    end
   end
   // Horizontal effects are not representable by one state per line. Reject,
   // rather than silently mixing states or pausing the emulated machine.
   if(midline && (palette!=line_palette || fine_x!=line_fine ||
                  pattern_mode!=line_mode || display_mask!=line_mask))errors[3]<=1;
   if((active || begin_packet) && ppu_ce && scanline>=8 && scanline<232 &&
      dot>=1 && dot<=256 && scroll_access)scroll_seen<=1;
   if(active && ppu_ce && scanline==232 && dot==1) begin
    active<=0;owned<=1;
    valid<=errors==0 && row_count==224 && !copy_busy && !source_fault;
    if(row_count!=224)errors[0]<=1;
    if(copy_busy)errors[1]<=1;
    if(source_fault)errors[5]<=1;
   end
   // A ROM fault may stop PPU CE entirely. Retire invalid without waiting for
   // a frame-end marker that will never arrive; no request/stall is generated.
   if((active || begin_packet) && source_fault) begin
    active<=0;owned<=1;valid<=0;copy_busy<=0;errors[5]<=1;
   end
  end
 end
endmodule
