// SPDX-License-Identifier: MIT
// One NES-clock lease for evaluated fetches, bounded geometry and raster state.
// geometry_valid does NOT mean CHR supplied, host ACKed, or display ready.
module nes_native_frame165(
 input wire clk,reset,release_frame,ppu_ce,rom_fault,
 input wire [8:0] scanline,dot,
 input wire bg_low,bg_high,obj_low,obj_high,obj_valid,extra_sprites,
 input wire [1:0] bg_attribute,input wire [7:0] obj_attribute,obj_x,
 input wire ppu_read,ppu_valid,input wire [13:0] logical_address,input wire [21:0] physical_address,
 input wire [14:0] scroll_v,scroll_t,input wire [2:0] fine_x,pattern_mode,
 input wire [7:0] display_mask,input wire [191:0] palette,input wire scroll_access,
 input wire query,input wire [2:0] query_kind,input wire [12:0] query_index,input wire [15:0] query_generation,
 output reg owned,geometry_valid,output wire initialized,active,output wire [15:0] generation,
 output reg [24:0] errors,output wire scroll_seen,
 output wire [7:0] row_count,object_count,exception_count,output wire [5:0] group_count,palette_count,
 output reg response,output wire hit,output wire [63:0] data
);
 wire fetch_owned,fetch_valid,fetch_event,fetch_response;wire [7:0] fetch_errors;
 wire [63:0] fetch_data;wire [1:0] required_kind;
 wire compact_owned,compact_valid,compact_response,compact_hit;wire [7:0] compact_errors;wire [63:0] compact_data;
 wire raster_owned,raster_valid,raster_response,raster_hit;wire [7:0] raster_errors,raster_rows;wire [55:0] raster_data;
 reg joining,fetch_owned_q;reg [2:0] selected;reg eligible;
 wire start=initialized && !active && !fetch_owned && !owned && ppu_ce && scanline==7 && dot==257;
 wire accept_query=query && owned && geometry_valid && query_generation==generation && !release_frame && !reset;
 nes_native_planes165 fetch(
  .clk(clk),.reset(reset),.release_scene(release_frame),.ppu_ce(ppu_ce),.rom_fault(rom_fault),
  .scanline(scanline),.dot(dot),.bg_low(bg_low),.bg_high(bg_high),.obj_low(obj_low),.obj_high(obj_high),
  .obj_valid(obj_valid),.extra_sprites(extra_sprites),.bg_attribute(bg_attribute),.obj_attribute(obj_attribute),.obj_x(obj_x),
  .ppu_read(ppu_read),.ppu_valid(ppu_valid),.logical_address(logical_address),.physical_address(physical_address),
  .query(accept_query && query_kind==6),.query_tile(query_index),
  .initialized(initialized),.active(active),.owned(fetch_owned),.valid(fetch_valid),.errors(fetch_errors),.generation(generation),
  .event_valid(fetch_event),.event_data(fetch_data),.response(fetch_response),.required_kind(required_kind));
 nes_native_compact_planes165 compact(
  .clk(clk),.reset(reset),.release_scene(release_frame),.begin_scene(start),
  .end_scene(fetch_owned&&!fetch_owned_q),.source_fault(rom_fault || (fetch_owned&&!fetch_valid)),
  .event_valid(fetch_event),.event_data(fetch_data),.query(accept_query && query_kind<4 && query_index<2048),
  .query_kind(query_kind[1:0]),.query_address(query_index[10:0]),
  .active(),.owned(compact_owned),.valid(compact_valid),.errors(compact_errors),
  .row_count(row_count),.object_count(object_count),.exception_count(exception_count),.group_count(group_count),
  .response(compact_response),.hit(compact_hit),.data(compact_data));
 // This specialized packet permits v/t accesses only as part of this joined
 // fetch/geometry lease. FineX, palette, mode and mask midline changes reject.
 nes_native_raster_frame165 raster(
  .clk(clk),.reset(reset),.release_packet(release_frame),.ppu_ce(ppu_ce&&(active||fetch_owned)),
  .scanline(scanline),.dot(dot),.scroll_v(scroll_v),.scroll_t(scroll_t),.fine_x(fine_x),.pattern_mode(pattern_mode),
  .display_mask(display_mask),.palette(palette),.scroll_access(scroll_access),.source_fault(rom_fault),
  .query(accept_query && ((query_kind==4 && query_index<224)||(query_kind==5 && query_index<1024))),
  .query_palette(query_kind==5),.query_row(query_index[7:0]),.query_bank(query_index[9:5]),.query_color(query_index[4:0]),
  .owned(raster_owned),.valid(raster_valid),.generation(),.errors(raster_errors),.row_count(raster_rows),
  .palette_count(palette_count),.response(raster_response),.hit(raster_hit),.data(raster_data),.scroll_seen(scroll_seen));
 wire member_hit=selected<4?(compact_response&&compact_hit):selected<6?(raster_response&&raster_hit):selected==6?fetch_response:1'b0;
 assign hit=response && eligible && geometry_valid && owned && member_hit && !release_frame && !reset;
 assign data=!hit?64'd0:selected<4?compact_data:selected<6?{8'd0,raster_data}:{62'd0,required_kind};
 always @(posedge clk)begin
  response<=0;
  if(reset || release_frame)begin
   owned<=0;geometry_valid<=0;errors<=0;joining<=0;fetch_owned_q<=0;selected<=0;eligible<=0;
  end else begin
   fetch_owned_q<=fetch_owned;
   if(start)begin joining<=1;errors<=0;geometry_valid<=0;end
   // A source fault may stop PPU CE before raster row8 exists. It must never
   // wait for that absent member. Shared release cancels every member.
   if((joining || start || owned) && rom_fault)begin
    owned<=1;geometry_valid<=0;joining<=0;errors<={1'b1,raster_errors,compact_errors,fetch_errors};
   end else if(joining && fetch_owned && !fetch_valid)begin
    owned<=1;geometry_valid<=0;joining<=0;errors<={raster_errors,compact_errors,fetch_errors};
   end else if(joining && fetch_owned && compact_owned && raster_owned)begin
    owned<=1;joining<=0;errors<={raster_errors,compact_errors,fetch_errors};
    geometry_valid<=fetch_valid && compact_valid && raster_valid && row_count==224 && raster_rows==224;
   end
   if(query && owned)begin response<=1;selected<=query_kind;eligible<=accept_query;end
  end
 end
endmodule
