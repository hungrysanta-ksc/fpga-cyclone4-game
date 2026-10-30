// SPDX-License-Identifier: MIT
//174 Actual pattern-load events. BG planes may use different physical tiles.
// Extended event: bit56=mixed,55:53=low fineY;15:13 remains high fineY.
// A different physical/logical tile, attribute, position or OBJ pair is rejected.
// Rows describe fetches; this stream still needs a bounded rendering consumer.
module nes_native_planes165(
 input wire clk,reset,release_scene,ppu_ce,rom_fault,
 input wire [8:0] scanline,dot,
 input wire bg_low,bg_high,obj_low,obj_high,obj_valid,extra_sprites,
 input wire [1:0] bg_attribute,
 input wire [7:0] obj_attribute,obj_x,
 input wire ppu_read,ppu_valid,input wire [13:0] logical_address,
 input wire [21:0] physical_address,
 //501: only PPUMASK rendering transitions authorize bounded raw rows.
 input wire [7:0] display_mask,
 input wire row_commit,row_patched,input wire [7:0] committed_row,
 output wire row_needs_patch,
 input wire query,input wire [12:0] query_tile,
 output reg initialized,active,owned,valid,
 output reg [7:0] errors,
 output reg [15:0] generation,
 output reg event_valid,output reg [63:0] event_data,
 output reg response,output wire [1:0] required_kind
);
 // One bit each for BG/OBJ, indexed by physical SMB3 CHR tile (128 KiB / 16).
 // Each lease is explicitly scrubbed; generation wrap cannot resurrect bits.
 (* ramstyle="M9K" *) reg [1:0] required_tiles[0:8191];
 reg [12:0] scrub;
 reg pending,last_write_valid,retiring;
 reg [12:0] pending_tile,last_tile;
 reg [1:0] pending_kind,last_value,tile_q;wire [1:0] pending_old=tile_q;
 wire [1:0] new_value=((last_write_valid && last_tile==pending_tile)?last_value:pending_old)|pending_kind;
 reg query_hit;
 // Query is accepted only while owned; capture mark occurs only while active.
 always @(posedge clk)tile_q<=required_tiles[owned?query_tile:physical_address[16:4]];
 assign required_kind=query_hit?tile_q:2'd0;
 reg pair_pending;
 reg [21:0] pair_address;
 reg [13:0] pair_logical;
 reg [63:0] pair_description;
 wire begin_frame=initialized && !active && !owned && !retiring && ppu_ce && scanline==7 && dot==257;
 wire end_frame=active && ppu_ce && scanline==232 && dot==1;
 wire capturing=active || begin_frame;
 wire low_event=bg_low || (obj_low && obj_valid);
 wire high_event=bg_high || (obj_high && obj_valid);
 wire is_obj=obj_low || obj_high;
 wire prefetch=dot>=321;
 wire [8:0] target_line=(is_obj || prefetch)?scanline+9'd1:scanline;
 // BG column is BEFORE fine-X subtraction. Use the displayed row's fine-X,
 // never the previous scanline's value that happened to be live at prefetch.
 wire [8:0] column=prefetch?((dot>=329)?9'd1:9'd0):(((dot+9'd7)>>3)+9'd1);
 wire relevant=target_line>=8 && target_line<232 && (is_obj || column<=32);
 wire [7:0] target_row=target_line-9'd8;
 wire [7:0] position=is_obj?obj_x:column[7:0];
 wire [7:0] attribute=is_obj?obj_attribute:{6'd0,bg_attribute};
 wire [2:0] rank=is_obj?((dot-9'd257)>>3):3'd0;
 wire [63:0] description={11'd0,rank,is_obj,attribute,position,target_row,
                          logical_address[12:4],physical_address[2:0],physical_address[16:4]};
 wire address_ok=ppu_read && ppu_valid && !logical_address[13] &&
                 physical_address[21:17]==5'h10 && logical_address[3:0]==physical_address[3:0];
 wire ordinary_pair=(physical_address==(pair_address^22'd8)) &&
                    (logical_address==(pair_logical^14'd8)) && description==pair_description;
 // Real SMB3 $2006 split can change fineY between the two BG plane loads.
 // Preserve both source rows, but keep tile, plane lane and geometry strict.
 wire bg_pair=!is_obj && description[52:25]==pair_description[52:25];
 wire pair_ok=pair_pending && address_ok && logical_address[3] && (ordinary_pair || bg_pair);
 wire cross_tile=pair_address[16:4]!=physical_address[16:4];
 wire mixed_planes=cross_tile || pair_address[2:0]!=physical_address[2:0];
 wire [63:0] plane_extension=mixed_planes?{7'd0,1'b1,pair_address[2:0],53'd0}:64'd0;
 wire [63:0] cross_description={2'd0,1'b1,pair_address[16:13],description[56:25],pair_address[12:4],description[15:0]};
 reg [1:0] previous_render;
 reg raw_current,raw_next,raw_proved;
 wire visible_line=scanline>=8 && scanline<232;
 wire line_edge=ppu_ce && dot==1;
 wire render_change=capturing && ppu_ce && display_mask[4:3]!=previous_render;
 wire raw_target=!is_obj && ((prefetch || dot<=1)?raw_next:raw_current);
 wire transition_target=!is_obj && render_change && (prefetch || dot<=257);
 wire raw_event=raw_target || transition_target;
 assign row_needs_patch=raw_current;
 wire cancel_pair=render_change && pair_pending && !pair_description[49] &&
   ((pair_description[32:25]==scanline-9'd8 && dot<=257) ||
    pair_description[32:25]==scanline-9'd7);
 wire mark_high=initialized && capturing && ppu_ce && relevant && high_event && pair_ok && !raw_event && !rom_fault && !extra_sprites;
 // Both sources enter the required set. A rejected frame cannot export it.
 // Low/high events are separated by PPU cycles; retain the RAM forwarding.
 wire mark_low=initialized && capturing && ppu_ce && relevant && low_event && address_ok && !logical_address[3] && !raw_event && !rom_fault && !extra_sprites;
 wire mark=mark_low || mark_high;
 // RAM accesses are separate from state reset. Query is synchronous and only
 // the sealed set is readable. The read/modify/write path forwards collisions.
 always @(posedge clk)begin
  if(!reset && !release_scene)begin
   if(!initialized)required_tiles[scrub]<=0;
   else if(pending)required_tiles[pending_tile]<=new_value;

  end
 end
 always @(posedge clk)begin
  event_valid<=0;response<=0;query_hit<=0;
  if(reset || release_scene)begin
   initialized<=0;scrub<=0;active<=0;owned<=0;valid<=0;retiring<=0;
   pending<=0;last_write_valid<=0;pair_pending<=0;errors<=0;event_data<=0;
   previous_render<=0;raw_current<=0;raw_next<=0;raw_proved<=0;
   if(reset)generation<=0;
  end else begin
   if(ppu_ce)previous_render<=display_mask[4:3];
   if(capturing && line_edge)begin
    if(raw_current && !raw_proved)errors[6]<=1;
    raw_current<=raw_next;raw_next<=0;raw_proved<=0;
   end
   if(capturing && row_commit && raw_current)begin
    if(!row_patched || committed_row!=scanline-9'd8 || !visible_line)errors[6]<=1;
    else raw_proved<=1;
   end
   if(render_change)begin
    if(visible_line && dot<=257)raw_current<=1;
    if(scanline>=7 && scanline<231)raw_next<=1;
    if(cancel_pair)pair_pending<=0;
   end
   pending<=mark;
   last_write_valid<=pending;
   if(pending)begin last_tile<=pending_tile;last_value<=new_value;end
   if(!initialized)begin
    if(scrub==8191)initialized<=1;
    else scrub<=scrub+1'b1;
   end
   if(begin_frame)begin
    active<=1;generation<=generation+1'b1;errors<=0;pair_pending<=0;
    raw_current<=0;raw_next<=render_change;raw_proved<=0;
   end
   if(capturing && ppu_ce && relevant && low_event)begin
    pair_pending<=!raw_event && address_ok && !logical_address[3];
    pair_address<=physical_address;pair_logical<=logical_address;pair_description<=description;
    if(pair_pending && !cancel_pair)errors[0]<=1;
    // No read during a rendering transition is not a bad ROM response.
    // Every actual read retains address, DATA-valid and logical/physical lane checks.
    if(raw_event)begin
     if(ppu_read && !address_ok)errors[1]<=1;
    end else if(!address_ok || logical_address[3])errors[1]<=1;
   end
   if(capturing && ppu_ce && relevant && high_event)begin
    pair_pending<=0;
    if(raw_event)begin
     // A restart can issue high-load while the valid ROM address is still
     // the low plane. Raw pixels preserve this PPU behavior; logical and
     // physical bus lanes must still match through address_ok.
     if(ppu_read && !address_ok)errors[2]<=1;
     if(pair_pending && !cancel_pair)errors[2]<=1;
    end else if(!pair_ok)errors[2]<=1;
   end
   if(mark)begin
    pending_tile<=physical_address[16:4];pending_kind<=is_obj?2'b10:2'b01;
    if(mark_high)begin event_valid<=1;event_data<=(cross_tile?cross_description:description)|plane_extension;end
   end
   if(capturing && extra_sprites)errors[3]<=1;
   // Source fault does not need another PPU clock-enable to retire the set.
   if(capturing && rom_fault)errors[4]<=1;
   if(end_frame || (capturing && rom_fault))begin
    active<=0;retiring<=1;
    if(pair_pending)errors[5]<=1;
    pair_pending<=0;
   end
   if(retiring && !pending)begin
    retiring<=0;owned<=1;valid<=errors==0;
   end
   if(query && owned)begin
    response<=1;
    if(valid)query_hit<=1;
   end
  end
 end
endmodule
