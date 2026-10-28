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
 output reg [31:0] display_serial373,output reg [2:0] display_raw373,
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
 reg armed,started,identity_pending,final_seen,cancelled,protocol_fault;
 reg capturing,materialized,committed,display_valid;
 reg [31:0] capture_epoch373,display_epoch373,next_serial373;
 reg [15:0] capture_gen373,display_gen373;
 reg [2:0] input_raw373;
 wire immutable373=source_ready&&source_is_rom&&!source_writing;
 wire cancel=stop||cancelled||protocol_fault||rom_fault||flow_error||export_error!=0;
 assign lease_fault=protocol_fault;
 assign captured_epoch=display_epoch373;assign captured_generation=display_gen373;
 assign waiting_display=display_valid&&!cancel;
 assign lease_valid=waiting_display&&immutable373&&live_epoch==display_epoch373;
 assign retire_permitted=lease_valid&&reader_drained;
 assign source_owned365=armed&&!cancel&&immutable373&&live_epoch==source_epoch&&
   (materialized||(owned&&geometry_valid&&generation==source_generation));
 assign source_start=!reset&&!cancel&&armed&&!started&&source_start_ready&&source_owned365;
 assign identity_valid=!reset&&!cancel&&display_valid&&identity_pending;
 assign prelease=!reset&&!cancel&&started&&!display_valid&&source_owned365;
 assign export_permitted=source_owned365&&started;
 assign effective_release=cancel||(capture_materialized366&&started&&!materialized&&!cancel);
 nes_native_frame201 #(.REQUIRED_BITMAP(REQUIRED_BITMAP)) frame(.release_frame(effective_release),.rom_fault(rom_fault||lease_fault),.*);
 always @(posedge clk)begin
  if(reset)begin
   armed<=0;started<=0;identity_pending<=0;final_seen<=0;cancelled<=0;protocol_fault<=0;
   capturing<=0;materialized<=0;committed<=0;display_valid<=0;
   capture_epoch373<=0;capture_gen373<=0;display_epoch373<=0;display_gen373<=0;
   source_epoch<=0;source_generation<=0;source_serial<=0;next_serial373<=1;
   display_serial373<=0;display_raw373<=0;input_raw373<=0;
  end else if(cancel)begin
   armed<=0;started<=0;identity_pending<=0;final_seen<=0;capturing<=0;
   materialized<=0;committed<=0;display_valid<=0;cancelled<=1;
  end else begin
   if(capture_begin)begin
    if(capturing||!immutable373)protocol_fault<=1;
    else begin capturing<=1;capture_epoch373<=live_epoch;capture_gen373<=generation+1'b1;end
   end
   if(capturing&&(!immutable373||live_epoch!=capture_epoch373))protocol_fault<=1;
   if(armed&&(!immutable373||live_epoch!=source_epoch||(!materialized&&generation!=source_generation)))protocol_fault<=1;
   if(display_valid&&(!immutable373||live_epoch!=display_epoch373))protocol_fault<=1;
   if(capturing&&owned&&geometry_valid&&!armed&&source_start_ready&&next_serial373!=32'hffffffff)begin
    if(generation!=capture_gen373)protocol_fault<=1;
    else begin armed<=1;source_epoch<=capture_epoch373;source_generation<=capture_gen373;
     source_serial<=next_serial373;input_raw373<=patch_count;
     // An invalid display context may carry this input's prelease hint identity.
     // A valid display context is immutable until its own final ACK/retire.
     if(!display_valid)begin display_epoch373<=capture_epoch373;display_gen373<=capture_gen373;
      display_serial373<=next_serial373;display_raw373<=patch_count;end
    end
   end
   if(source_start)started<=1;
   if(capture_materialized366)begin
    if(!started||materialized||!source_owned365)protocol_fault<=1;
    else begin materialized<=1;capturing<=0;end
   end
   if(source_done)begin
    if(!started||!materialized||committed)protocol_fault<=1;
    else begin committed<=1;next_serial373<=next_serial373+1'b1;end
   end
   if(committed&&!display_valid)begin
    display_epoch373<=source_epoch;display_gen373<=source_generation;display_serial373<=source_serial;
    display_raw373<=input_raw373;display_valid<=1;identity_pending<=1;final_seen<=0;
    armed<=0;started<=0;materialized<=0;committed<=0;
   end else if(identity_valid&&identity_ready)identity_pending<=0;
   if(display_ack)begin if(!display_valid)protocol_fault<=1;else final_seen<=1;end
   if(retire_commit)begin
    if(!display_valid||!(final_seen||display_ack)||!retire_permitted||retire_generation!=display_gen373)protocol_fault<=1;
    else begin
     display_valid<=0;identity_pending<=0;final_seen<=0;
     if(armed)begin display_epoch373<=source_epoch;display_gen373<=source_generation;
      display_serial373<=source_serial;display_raw373<=input_raw373;end
    end
   end
  end
 end
endmodule
