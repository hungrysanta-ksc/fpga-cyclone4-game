// SPDX-License-Identifier: MIT
// Shared functional/board capture -> source -> display admission boundary.
// Collector context may advance while the admitted source/display context stays
// frozen until final display ACK AND drained plan retirement. STOP is sticky
// until reset; a late source DONE cannot publish identity or release a new frame.
module nes_native_capture365 #(parameter EARLY_RELEASE=0, REQUIRED_BITMAP=1)(
 input wire clk,reset,stop,source_start_ready,source_done,identity_ready,display_ack,
 input wire source_ready,source_is_rom,source_writing,input wire [31:0] live_epoch,
 input wire [3:0] export_error,input wire flow_error,reader_drained,retire_commit,
 input wire capture_materialized366,
 input wire [15:0] retire_generation,
 output wire source_start,identity_valid,prelease,source_owned365,
 output reg [31:0] source_epoch,source_serial,output reg [15:0] source_generation,
 output wire effective_release,lease_valid,retire_permitted,export_permitted,waiting_display,lease_fault,
 output wire [31:0] captured_epoch,output wire [15:0] captured_generation,
 input wire ppu_ce,rom_fault,input wire [8:0] scanline,dot,
 input wire [5:0] color,input wire [2:0] emphasis,
 input wire bg_low,bg_high,obj_low,obj_high,obj_valid,extra_sprites,
 input wire [1:0] bg_attribute,input wire [7:0] obj_attribute,obj_x,
 input wire ppu_read,ppu_valid,input wire [13:0] logical_address,input wire [21:0] physical_address,
 input wire [14:0] scroll_v,scroll_t,input wire [2:0] fine_x,pattern_mode,
 input wire [7:0] display_mask,input wire [191:0] palette,input wire scroll_access,
 input wire query,input wire [2:0] query_kind,input wire [12:0] query_index,input wire [15:0] query_generation,
 output wire capture_begin,owned,geometry_valid,initialized,active,output wire [15:0] generation,
 output wire [24:0] errors,observe_errors180,output wire observe_collecting180,scroll_seen,
 output wire [7:0] row_count,object_count,exception_count,output wire [5:0] group_count,palette_count,
 output wire response,hit,output wire [63:0] data,
 output wire [7:0] patch_errors,output wire [2:0] patch_count
);
 wire ownership_fault,input_ready365;wire [31:0] input_epoch365;wire [15:0] input_generation365;
 wire local_source365;
 reg armed,started,identity_pending,final_seen,cancelled,protocol_fault;
 wire cancel=stop||cancelled||protocol_fault||ownership_fault||rom_fault||flow_error||export_error!=0;
 assign lease_fault=ownership_fault||protocol_fault;
 assign source_owned365=!reset&&!cancel&&(local_source365||(input_ready365&&source_epoch==input_epoch365&&source_generation==input_generation365));
 assign source_start=!reset&&!cancel&&armed&&!started&&input_ready365&&source_start_ready&&source_owned365;
 assign identity_valid=!reset&&!cancel&&identity_pending&&waiting_display;
 assign prelease=!reset&&!cancel&&started&&source_owned365&&!waiting_display;
 wire accepted_done=source_done&&started&&!cancel;
 wire accepted_retire=retire_commit&&(final_seen||display_ack)&&!cancel;
 nes_native_frame201 #(.REQUIRED_BITMAP(REQUIRED_BITMAP)) frame(.release_frame(effective_release),.rom_fault(rom_fault||lease_fault),.*);
 generate if(EARLY_RELEASE)begin: early366
 nes_capture_lease366 ownership(
  .clk(clk),.reset(reset),.stop(cancel),.capture_begin(capture_begin),
  .frame_owned(owned),.geometry_valid(geometry_valid),.frame_generation(generation),
  .materialize366(capture_materialized366&&started&&!cancel),.export_release(accepted_done),.export_error(export_error),
  .source_ready(source_ready),.source_is_rom(source_is_rom),.source_writing(source_writing),.live_epoch(live_epoch),
  .reader_drained(reader_drained),.retire_commit(accepted_retire),.retire_generation(retire_generation),
  .release_frame(effective_release),.lease_valid(lease_valid),.retire_permitted(retire_permitted),.export_permitted(export_permitted),
  .captured_epoch(captured_epoch),.captured_generation(captured_generation),.waiting_display(waiting_display),.fault(ownership_fault),
  .input_ready365(input_ready365),.input_epoch365(input_epoch365),.input_generation365(input_generation365),.local_source366(local_source365));
 end else begin: original365
 assign local_source365=1'b0;
 nes_capture_lease201 ownership(
  .clk(clk),.reset(reset),.stop(cancel),.capture_begin(capture_begin),
  .frame_owned(owned),.geometry_valid(geometry_valid),.frame_generation(generation),
  .export_release(accepted_done),.export_error(export_error),
  .source_ready(source_ready),.source_is_rom(source_is_rom),.source_writing(source_writing),.live_epoch(live_epoch),
  .reader_drained(reader_drained),.retire_commit(accepted_retire),.retire_generation(retire_generation),
  .release_frame(effective_release),.lease_valid(lease_valid),.retire_permitted(retire_permitted),.export_permitted(export_permitted),
  .captured_epoch(captured_epoch),.captured_generation(captured_generation),.waiting_display(waiting_display),.fault(ownership_fault),
  .input_ready365(input_ready365),.input_epoch365(input_epoch365),.input_generation365(input_generation365));
 end endgenerate
 always @(posedge clk)begin
  if(reset)begin
   armed<=0;started<=0;identity_pending<=0;final_seen<=0;cancelled<=0;protocol_fault<=0;
   source_epoch<=0;source_generation<=0;source_serial<=1;
  end else if(cancel)begin
   armed<=0;started<=0;identity_pending<=0;final_seen<=0;cancelled<=1;
   // Preserve the originating ownership error when STOP clears its lease FSM.
   if(ownership_fault)protocol_fault<=1;
  end else begin
   if(!armed&&input_ready365&&source_start_ready)begin
    armed<=1;source_epoch<=input_epoch365;source_generation<=input_generation365;
   end
   if(source_start)started<=1;
   if(accepted_done)identity_pending<=1;
   else if(identity_valid&&identity_ready)identity_pending<=0;
   if(display_ack)final_seen<=1;
   if(source_done&&!started)protocol_fault<=1;
   if(retire_commit)begin
    if(!(final_seen||display_ack)||!retire_permitted||!armed)protocol_fault<=1;
    else begin
     armed<=0;started<=0;identity_pending<=0;final_seen<=0;
     if(source_serial>=32'hfffffffe)protocol_fault<=1;else source_serial<=source_serial+1'b1;
    end
   end
  end
 end
endmodule
