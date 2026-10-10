// SPDX-License-Identifier: MIT
// Final PPU pixels, independent of mapper/scroll/sprite implementation.
// One frozen 256x224 snapshot. Crop NES rows 8..231; emphasis is not applied.
// Reader must release only AFTER its complete DMA; no overwrite while owned.
module nes_game_frame150(
 input wire nes_clk,host_clk,reset,
 input wire [8:0] cycle,scanline,input wire [5:0] color,
 input wire release_frame,
 output reg ready,
 input wire request,input wire [15:0] byte_address,
 output reg response,output reg [7:0] data
);
 // Asynchronous assertion, local host-clock release. NES reset is already
 // released by core_release in its own domain at the physical top.
 (* async_reg="true" *) reg [1:0] host_release;
 always @(posedge host_clk or posedge reset)
  if(reset)host_release<=0;else host_release<={host_release[0],1'b1};
 wire host_reset=!host_release[1];

 reg [8:0] old_cycle,old_line;
 reg capturing,waiting,publish_toggle;
 reg release_toggle;
 (* async_reg="true" *) reg release_meta,release_sync;
 (* async_reg="true" *) reg publish_meta,publish_sync;
 reg release_seen,publish_seen;
 reg [14:0] write_address;
 reg [1:0] group_pixel;
 reg [11:0] packed_pixels;
 wire new_pixel=(cycle!=old_cycle || scanline!=old_line) &&
   cycle>=2 && cycle<=257 && scanline>=8 && scanline<232;
 wire begin_frame=new_pixel && cycle==2 && scanline==8 && !waiting && !capturing;
 wire take_pixel=new_pixel && (capturing || begin_frame);
 wire write_enable=take_pixel && (group_pixel==2 || cycle==257);
 wire [17:0] write_data=cycle==257?{12'd0,color}:{color,packed_pixels};
 always @(posedge nes_clk or posedge reset)begin
  if(reset)begin
   old_cycle<=511;old_line<=511;capturing<=0;waiting<=0;publish_toggle<=0;
   release_meta<=0;release_sync<=0;release_seen<=0;
   write_address<=0;group_pixel<=0;packed_pixels<=0;
  end else begin
   release_meta<=release_toggle;release_sync<=release_meta;
   old_cycle<=cycle;old_line<=scanline;
   if(release_sync!=release_seen)begin release_seen<=release_sync;waiting<=0;end
   if(begin_frame)begin capturing<=1;write_address<=0;end
   if(take_pixel)begin
    if(group_pixel==0)packed_pixels[5:0]<=color;
    if(group_pixel==1)packed_pixels[11:6]<=color;
    if(write_enable)begin write_address<=write_address+1'b1;group_pixel<=0;end
    else group_pixel<=group_pixel+1'b1;
    if(scanline==231 && cycle==257)begin
     capturing<=0;waiting<=1;publish_toggle<=!publish_toggle;
     write_address<=0;
    end
   end
  end
 end
 // 19264 words, explicitly split into 38 physical 512x18 M9Ks. A monolithic
 // 19264-depth declaration may be rounded to 32768 and exceed this FPGA.
 reg [14:0] read_address;
 wire [17:0] bank_data[0:37];
 reg [5:0] read_bank;
 genvar b;
 generate for(b=0;b<38;b=b+1)begin: banks
  (* ramstyle="M9K, no_rw_check" *) reg [17:0] memory[0:511];
  reg [17:0] q;
  always @(posedge nes_clk)
   if(!reset && write_enable && write_address[14:9]==b)
    memory[write_address[8:0]]<=write_data;
  always @(posedge host_clk)q<=memory[read_address[8:0]];
  assign bank_data[b]=q;
 end endgenerate
 always @(posedge host_clk)read_bank<=read_address[14:9];
 wire [17:0] read_data=read_bank<38?bank_data[read_bank]:18'd0;
 // SNES 8bpp tile layout. Six NES index bits, upper two planes always zero.
 wire [4:0] tile_x=byte_address[10:6];
 wire [7:0] row={byte_address[15:11],byte_address[3:1]};
 wire [7:0] pixel_x={tile_x,3'b0};
 wire [2:0] requested_plane={byte_address[5:4],byte_address[0]};
 // A32-entry constant lookup avoids a generic divide-by-three network.
 function [8:0] column_word(input [4:0] tile);
  begin case(tile)
   5'd0:column_word={2'd0,7'd0};
   5'd1:column_word={2'd2,7'd2};
   5'd2:column_word={2'd1,7'd5};
   5'd3:column_word={2'd0,7'd8};
   5'd4:column_word={2'd2,7'd10};
   5'd5:column_word={2'd1,7'd13};
   5'd6:column_word={2'd0,7'd16};
   5'd7:column_word={2'd2,7'd18};
   5'd8:column_word={2'd1,7'd21};
   5'd9:column_word={2'd0,7'd24};
   5'd10:column_word={2'd2,7'd26};
   5'd11:column_word={2'd1,7'd29};
   5'd12:column_word={2'd0,7'd32};
   5'd13:column_word={2'd2,7'd34};
   5'd14:column_word={2'd1,7'd37};
   5'd15:column_word={2'd0,7'd40};
   5'd16:column_word={2'd2,7'd42};
   5'd17:column_word={2'd1,7'd45};
   5'd18:column_word={2'd0,7'd48};
   5'd19:column_word={2'd2,7'd50};
   5'd20:column_word={2'd1,7'd53};
   5'd21:column_word={2'd0,7'd56};
   5'd22:column_word={2'd2,7'd58};
   5'd23:column_word={2'd1,7'd61};
   5'd24:column_word={2'd0,7'd64};
   5'd25:column_word={2'd2,7'd66};
   5'd26:column_word={2'd1,7'd69};
   5'd27:column_word={2'd0,7'd72};
   5'd28:column_word={2'd2,7'd74};
   5'd29:column_word={2'd1,7'd77};
   5'd30:column_word={2'd0,7'd80};
   5'd31:column_word={2'd2,7'd82};
  endcase end
 endfunction
 reg [14:0] row_base;
 reg [6:0] column_base;
 wire [8:0] column_lookup=column_word(tile_x);
 reg [2:0] plane;
 reg [3:0] state;
 reg [1:0] first_pixel;
 reg [71:0] window;
 integer i;
 always @(posedge host_clk or posedge host_reset)begin
  if(host_reset)begin
   publish_meta<=0;publish_sync<=0;publish_seen<=0;
   release_toggle<=0;ready<=0;response<=0;data<=0;
   read_address<=0;row_base<=0;column_base<=0;state<=0;plane<=0;first_pixel<=0;window<=0;
  end else begin
   publish_meta<=publish_toggle;publish_sync<=publish_meta;response<=0;
   if(publish_sync!=publish_seen)begin publish_seen<=publish_sync;ready<=1;end
   if(release_frame && ready)begin
    ready<=0;release_toggle<=!release_toggle;state<=0;
   end else case(state)
    0:if(request && ready)begin
     if(byte_address>=57344 || requested_plane>=6)begin data<=0;response<=1;end
     else begin
      row_base<=row*15'd86;column_base<=column_lookup[6:0];
      first_pixel<=column_lookup[8:7];plane<=requested_plane;state<=7;
     end
    end
    7:begin read_address<=row_base+column_base;state<=1;end
    1:begin read_address<=read_address+1'b1;state<=2;end
    2:begin window[17:0]<=read_data;read_address<=read_address+1'b1;state<=3;end
    3:begin window[35:18]<=read_data;read_address<=read_address+1'b1;state<=4;end
    4:begin window[53:36]<=read_data;state<=5;end
    5:begin window[71:54]<=read_data;state<=6;end
    6:begin
     for(i=0;i<8;i=i+1)data[7-i]<=window[(i+first_pixel)*6+plane];
     response<=1;state<=0;
    end
    default:state<=0;
   endcase
  end
 end
endmodule
