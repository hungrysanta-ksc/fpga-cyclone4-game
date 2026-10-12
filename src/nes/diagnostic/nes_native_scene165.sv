// SPDX-License-Identifier: MIT
// One NES-domain lease for CHR cache, raster state and a 2KiB CIRAM + 256B OAM
// snapshot. snapshot_valid is NOT complete-frame readiness: required CHR tags,
// partial tiles, mapper/raster versions and SNES rendering remain separate.
module nes_native_scene165(
 input wire clk,reset,ppu_ce,ppu_read,ppu_valid,rom_fault,
 input wire [13:0] ppu_logical,input wire [21:0] ppu_physical,input wire [7:0] ppu_data,
 input wire [8:0] scanline,dot,
 input wire [14:0] scroll_v,scroll_t,input wire [2:0] fine_x,pattern_mode,
 input wire [7:0] display_mask,input wire [191:0] palette,input wire scroll_access,
 // CIRAM synchronous read, OAM combinational read. Neither address can write.
 output wire [10:0] nt_address,input wire [7:0] nt_data,input wire nt_write,
 output wire [7:0] oam_address,input wire [7:0] oam_data,input wire oam_write,
 input wire release_scene,
 input wire chr_query,input wire [8:0] chr_slot,input wire [17:0] chr_tag,
 input wire [4:0] chr_offset,input wire chr_obj4,
 output wire chr_response,chr_hit,output wire [7:0] chr_data,output wire [15:0] chr_mask,
 input wire state_query,state_palette,input wire [7:0] state_row,
 input wire [4:0] state_bank,state_color,
 output wire state_response,state_hit,output wire [55:0] state_data,
 input wire memory_query,input wire [11:0] memory_address,
 output reg memory_response,memory_hit,output reg [7:0] memory_data,
 output reg owned,snapshot_valid,output wire [15:0] generation,
 output wire [7:0] raster_errors,output reg [2:0] memory_errors,
 output wire [7:0] row_count,output wire [5:0] palette_count
);
 wire initialized,chr_owned,raster_owned,raster_valid;
 wire cache_hit,packet_hit;wire [7:0] cache_data;wire [15:0] cache_mask;wire [55:0] packet_data;
 assign chr_hit=cache_hit && snapshot_valid;
 assign chr_data=snapshot_valid?cache_data:8'd0;
 assign chr_mask=snapshot_valid?cache_mask:16'd0;
 assign state_hit=packet_hit && snapshot_valid;
 assign state_data=snapshot_valid?packet_data:56'd0;
 reg active,retiring,copying,copy_pending,copy_done;
 reg [11:0] cursor,pending_address;
 reg [7:0] oam_registered;
 (* ramstyle="M9K" *) reg [7:0] memory[0:2303];
 wire qualified_ce=ppu_ce && initialized;
 wire begin_scene=qualified_ce && scanline==8 && dot==1 && !active && !retiring && !owned;
 wire end_scene=active && ((qualified_ce && scanline==232 && dot==1) || rom_fault);
 assign nt_address=cursor[10:0];
 assign oam_address=cursor[7:0];
 nes_native_tap165 cache(
  .clk(clk),.reset(reset),.ppu_ce(ppu_ce),.ppu_read(ppu_read),.ppu_valid(ppu_valid),
  .rom_fault(rom_fault),.ppu_logical(ppu_logical),.ppu_physical(ppu_physical),.ppu_data(ppu_data),
  .freeze(end_scene || (begin_scene && rom_fault)),.release_cache(release_scene),
  .query(chr_query && owned),.query_slot(chr_slot),.query_tag(chr_tag),.query_offset(chr_offset),.query_obj4(chr_obj4),
  .initialized(initialized),.owned(chr_owned),.response(chr_response),.hit(cache_hit),.data(cache_data),.valid_bytes(cache_mask));
 nes_native_raster165 raster(
  .clk(clk),.reset(reset),.ppu_ce(qualified_ce),.scanline(scanline),.dot(dot),
  .scroll_v(scroll_v),.scroll_t(scroll_t),.fine_x(fine_x),.pattern_mode(pattern_mode),
  .display_mask(display_mask),.palette(palette),.scroll_access(scroll_access),.source_fault(rom_fault),
  .release_packet(release_scene),.query(state_query && owned),.query_palette(state_palette),
  .query_row(state_row),.query_bank(state_bank),.query_color(state_color),
  .owned(raster_owned),.valid(raster_valid),.generation(generation),.errors(raster_errors),
  .row_count(row_count),.palette_count(palette_count),.response(state_response),.hit(packet_hit),.data(packet_data));
 always @(posedge clk)begin
  // Separate RAM process: no RAM reset and no game-port ownership changes.
  if(copy_pending && !reset && !release_scene)
   memory[pending_address]<=pending_address<2048?nt_data:oam_registered;
  oam_registered<=oam_data;
 end
 always @(posedge clk)begin
  memory_response<=0;memory_hit<=0;memory_data<=0;
  if(reset)begin
   owned<=0;snapshot_valid<=0;active<=0;retiring<=0;copying<=0;copy_pending<=0;copy_done<=0;
   cursor<=0;pending_address<=0;memory_errors<=0;
  end else if(release_scene)begin
   owned<=0;snapshot_valid<=0;active<=0;retiring<=0;copying<=0;copy_pending<=0;copy_done<=0;
   cursor<=0;memory_errors<=0;
  end else begin
   copy_pending<=copying;
   if(copying)begin
    pending_address<=cursor;
    if(cursor==2303)copying<=0;
    else cursor<=cursor+1'b1;
   end
   if(copy_pending && pending_address==2303)copy_done<=1;
   if(begin_scene)begin
    active<=1;copying<=1;copy_pending<=0;copy_done<=0;cursor<=0;memory_errors<=0;
   end
   if((active || begin_scene) && nt_write)memory_errors[0]<=1;
   if((active || begin_scene) && oam_write)memory_errors[1]<=1;
   if(end_scene || (begin_scene && rom_fault))begin
    active<=0;retiring<=1;copying<=0;copy_pending<=0;
    if(!copy_done || begin_scene)memory_errors[2]<=1;
   end
   // Wait for the CHR metadata drain and raster seal, never just the last
   // observed pixel. All three clients share reset/release and query gating.
   if(retiring && chr_owned && raster_owned)begin
    retiring<=0;owned<=1;
    snapshot_valid<=raster_valid && copy_done && memory_errors==0;
   end
   if(memory_query && owned)begin
    memory_response<=1;
    if(snapshot_valid && memory_address<2304)begin
     memory_hit<=1;memory_data<=memory[memory_address];
    end
   end
  end
 end
endmodule
