// SPDX-License-Identifier: MIT
//047 restricted actual-core PPU tap. All ports belong to queue_clk.
module nes_ncr1_ppu_tap(
 input wire queue_clk,reset,arm,immutable_chr,chr_32k,
 input wire tap_ce,tap_bgp,tap_mode,
 input wire [8:0] cycle,scanline,
 input wire [2:0] tap_fine,
 input wire [14:0] tap_scroll,
 input wire [95:0] tap_palette,
 input wire [1:0] tap_attribute,
 input wire tap_ppu_change,tap_mapper_change,
 input wire ppumem_read,ppumem_write,
 input wire [21:0] ppumem_addr,
 output wire frame_start,frame_end,supported_mode,bg_valid,
 output reg [7:0] frame_id,
 output wire [2:0] fine_x,
 output wire [63:0] palette_snes,
 output wire signed [8:0] bg_line,
 output wire [8:0] bg_dot,
 output wire [14:0] bg_chr_address,
 output wire [1:0] bg_palette,
 output wire [31:0] bg_tick,
 output reg tap_fault,
 output reg [7:0] tap_error
);
 reg active;reg [2:0] fine_q;reg [31:0] ticks;
 wire begin_frame=arm && tap_ce && scanline==511 && cycle==1;
 wire end_frame=active && tap_ce && scanline==240 && cycle==1;
 // This diagnostic palette is repeated in all four BG groups. Canonicalizing
 // actual attribute0..3 to group0 is valid ONLY while every group matches.
 wire palette_ok=tap_palette==96'h5b084f5b084f5b084f5b084f;
 wire mode_ok=immutable_chr && tap_mode && tap_scroll==0 && palette_ok;
 wire changed=(tap_ce && tap_ppu_change) || tap_mapper_change ||
              (ppumem_write && ppumem_addr<22'h208000);
 wire raw_bg=active && tap_ce && tap_bgp && (scanline<240 || scanline==511) &&
             (cycle[2:0]==6 || cycle[2:0]==0);
 wire address_ok=ppumem_read && ppumem_addr>=22'h200000 &&
                 ppumem_addr<(chr_32k?22'h208000:22'h204000);
 assign frame_start=!reset && !tap_fault && begin_frame;
 assign frame_end=!reset && !tap_fault && end_frame;
 assign supported_mode=!tap_fault && mode_ok && !(active && (changed || tap_fine!=fine_q)) &&
                       !(raw_bg && !address_ok);
 assign bg_valid=!reset && !tap_fault && raw_bg;
 assign bg_line=$signed(scanline);assign bg_dot=cycle-9'd1;
 assign bg_chr_address=ppumem_addr[14:0];
 // Attribute value is deliberately consumed via palette-group equivalence.
 // Unknown input attributes are rejected by simulation assertions in the binding TB.
 assign bg_palette=palette_ok ? (tap_attribute & 2'b00) : tap_attribute;
 assign fine_x=tap_fine;assign palette_snes=64'h10d67fff7eac0000;
 assign bg_tick=ticks;
 always @(posedge queue_clk)begin
  if(reset)begin active<=0;fine_q<=0;ticks<=0;frame_id<=1;tap_fault<=0;tap_error<=0;end
  else begin
   ticks<=ticks+1'b1;
   if(begin_frame)begin active<=1;fine_q<=tap_fine;end
   if(end_frame)begin active<=0;frame_id<=frame_id==4?1:frame_id+1'b1;end
   if(!tap_fault && (active || begin_frame))begin
    if(!mode_ok)begin tap_fault<=1;tap_error<=1;end
    else if(active && (changed || tap_fine!=fine_q))begin tap_fault<=1;tap_error<=2;end
    else if(raw_bg && !address_ok)begin tap_fault<=1;tap_error<=3;end
   end
  end
 end
endmodule
