// SPDX-License-Identifier: MIT
// One NES-clock lease for evaluated fetches, bounded geometry and raster state.
// geometry_valid does NOT mean CHR supplied, host ACKed, or display ready.
//201: identical181 capture; expose its exact start edge for source epoch ownership.
// Query7 reads raw slot/x; raster bits49..52 require a NEW wire version.
module nes_native_frame201 #(parameter REQUIRED_BITMAP=1)(
 input wire clk,reset,release_frame,ppu_ce,rom_fault,
 input wire [8:0] scanline,dot,input wire [5:0] color,input wire [2:0] emphasis,
 input wire bg_low,bg_high,obj_low,obj_high,obj_valid,extra_sprites,
 input wire [1:0] bg_attribute,input wire [7:0] obj_attribute,obj_x,
 input wire ppu_read,ppu_valid,input wire [13:0] logical_address,input wire [21:0] physical_address,
 input wire [14:0] scroll_v,scroll_t,input wire [2:0] fine_x,pattern_mode,
 input wire [7:0] display_mask,input wire [191:0] palette,input wire scroll_access,
 input wire query,input wire [2:0] query_kind,input wire [12:0] query_index,input wire [15:0] query_generation,
 output wire capture_begin,output reg owned,geometry_valid,output wire initialized,active,output wire [15:0] generation,
 output reg [24:0] errors,output wire [24:0] observe_errors180,
 output wire observe_collecting180,output wire scroll_seen,
 output wire [7:0] row_count,object_count,exception_count,output wire [5:0] group_count,palette_count,
 output reg response,output wire hit,output wire [63:0] data,
 output wire [7:0] patch_errors,output wire [2:0] patch_count
);
 wire fetch_owned,fetch_valid,fetch_event,fetch_response;wire [7:0] fetch_errors;
 wire [63:0] fetch_data;wire [1:0] required_kind;
 wire compact_owned,compact_valid,compact_response,compact_hit;wire [7:0] compact_errors;wire [63:0] compact_data;
 wire raster_owned,raster_valid,raster_response,raster_hit;wire [7:0] raster_errors,raster_rows;wire [55:0] raster_data;
 reg joining,fetch_owned_q;reg [2:0] selected;reg eligible;
 wire patch_owned,patch_valid,patch_response,patch_hit,row_finish,row_commit,row_patched;
 wire [7:0] committed_row;wire [2:0] row_slot;wire [5:0] patch_data;
 wire compact_patch,raster_patch;
 wire start=initialized && !active && !fetch_owned && !owned && ppu_ce && scanline==7 && dot==257;
 assign capture_begin=start&&!reset&&!release_frame;
 wire accept_query=query && owned && geometry_valid && query_generation==generation && !release_frame && !reset;
 nes_native_planes165 #(.REQUIRED_BITMAP(REQUIRED_BITMAP)) fetch(
  .clk(clk),.reset(reset),.release_scene(release_frame),.ppu_ce(ppu_ce),.rom_fault(rom_fault),
  .scanline(scanline),.dot(dot),.bg_low(bg_low),.bg_high(bg_high),.obj_low(obj_low),.obj_high(obj_high),
  .obj_valid(obj_valid),.extra_sprites(extra_sprites),.bg_attribute(bg_attribute),.obj_attribute(obj_attribute),.obj_x(obj_x),
  .ppu_read(ppu_read),.ppu_valid(ppu_valid),.logical_address(logical_address),.physical_address(physical_address),
  .query(REQUIRED_BITMAP && accept_query && query_kind==6),.query_tile(query_index),
  .initialized(initialized),.active(active),.owned(fetch_owned),.valid(fetch_valid),.errors(fetch_errors),.generation(generation),
  .event_valid(fetch_event),.event_data(fetch_data),.response(fetch_response),.required_kind(required_kind));
 nes_patch_capture181 pixels(
  .clk(clk),.reset(reset),.release_frame(release_frame),.begin_frame(start),
  .source_fault(rom_fault || (fetch_owned&&!fetch_valid)),.ppu_ce(ppu_ce),
  .generation_in(generation+16'd1),.scanline(scanline),.dot(dot),.color(color),.emphasis(emphasis),
  .need_patch(row_finish && (raster_patch || compact_patch)),
  .query(accept_query && query_kind==7 && query_index<2048),.query_generation(query_generation),
  .query_slot(query_index[10:8]),.query_x(query_index[7:0]),
  .active(),.owned(patch_owned),.valid(patch_valid),.generation(),.errors(patch_errors),.count(patch_count),
  .row_commit(row_commit),.row_patched(row_patched),.committed_row(committed_row),.row_slot(row_slot),
  .response(patch_response),.hit(patch_hit),.data(patch_data),.row_finish(row_finish));
 nes_native_compact181 compact(
  .clk(clk),.reset(reset),.release_scene(release_frame),.begin_scene(start),
  .end_scene(fetch_owned&&!fetch_owned_q),.source_fault(rom_fault || (fetch_owned&&!fetch_valid)),
  .row_commit(row_commit),.row_patched(row_patched),.committed_row(committed_row),.row_needs_patch(compact_patch),
  .event_valid(fetch_event),.event_data(fetch_data),.query(accept_query && query_kind<4 && query_index<2048),
  .query_kind(query_kind[1:0]),.query_address(query_index[10:0]),
  .active(),.owned(compact_owned),.valid(compact_valid),.errors(compact_errors),
  .row_count(row_count),.object_count(object_count),.exception_count(exception_count),.group_count(group_count),
  .response(compact_response),.hit(compact_hit),.data(compact_data));
 // Raster differences choose a complete raw row instead of poisoning later
 // rows. Source, palette capacity and unsupported emphasis still reject.
 nes_native_raster181 raster(
  .begin_packet(start),.end_packet(fetch_owned&&!fetch_owned_q),
  .row_commit(row_commit),.row_patched(row_patched),.committed_row(committed_row),.row_slot(row_slot),
  .row_needs_patch(raster_patch),
  .clk(clk),.reset(reset),.release_packet(release_frame),.ppu_ce(ppu_ce&&(active||fetch_owned)),
  .scanline(scanline),.dot(dot),.scroll_v(scroll_v),.scroll_t(scroll_t),.fine_x(fine_x),.pattern_mode(pattern_mode),
  .display_mask(display_mask),.palette(palette),.scroll_access(scroll_access),.source_fault(rom_fault),
  .query(accept_query && ((query_kind==4 && query_index<224)||(query_kind==5 && query_index<1024))),
  .query_palette(query_kind==5),.query_row(query_index[7:0]),.query_bank(query_index[9:5]),.query_color(query_index[4:0]),
  .owned(raster_owned),.valid(raster_valid),.errors(raster_errors),.row_count(raster_rows),
  .palette_count(palette_count),.response(raster_response),.hit(raster_hit),.data(raster_data),.scroll_seen(scroll_seen));
 assign observe_errors180={rom_fault,raster_errors,compact_errors,fetch_errors};
 assign observe_collecting180=joining || owned;
 wire member_hit=selected<4?(compact_response&&compact_hit):selected<6?(raster_response&&raster_hit):selected==6?fetch_response:(patch_response&&patch_hit);
 assign hit=response && eligible && geometry_valid && owned && member_hit && patch_valid && !rom_fault && !release_frame && !reset;
 assign data=!hit?64'd0:selected<4?compact_data:selected<6?{8'd0,raster_data}:selected==6?{62'd0,required_kind}:{58'd0,patch_data};
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
   end else if(joining && fetch_owned && compact_owned && raster_owned && patch_owned)begin
    owned<=1;joining<=0;errors<={raster_errors,compact_errors,fetch_errors};
    geometry_valid<=fetch_valid && compact_valid && raster_valid && patch_valid && row_count==224 && raster_rows==224;
   end
   if(query && owned)begin response<=1;selected<=query_kind;eligible<=accept_query;end
  end
 end
endmodule
