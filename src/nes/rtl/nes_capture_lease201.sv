// SPDX-License-Identifier: MIT
// NES-domain ownership split: exported MCU geometry + immutable ROM lease,
// while the existing collector captures one following frame. No extra frame RAM.
module nes_capture_lease201(
 input wire clk,reset,stop,capture_begin,
 input wire frame_owned,geometry_valid,input wire [15:0] frame_generation,
 input wire export_release,input wire [3:0] export_error,
 input wire source_ready,source_is_rom,source_writing,input wire [31:0] live_epoch,
 input wire reader_drained,retire_commit,input wire [15:0] retire_generation,
 output wire release_frame,lease_valid,retire_permitted,export_permitted,
 output reg [31:0] captured_epoch,output reg [15:0] captured_generation,
 output reg waiting_display,output reg fault
);
 reg capturing;reg [31:0] capture_epoch;reg [15:0] capture_generation;
 wire immutable=source_ready&&source_is_rom&&!source_writing;
 wire capture_ok=immutable&&capture_epoch==live_epoch;
 wire generation_ok=frame_generation==capture_generation;
 wire commit=export_release&&export_error==0&&geometry_valid;
 wire lost=(capturing&&(!capture_ok||(frame_owned&&!generation_ok)))||
           (waiting_display&&(!immutable||captured_epoch!=live_epoch));
 wire bad_retire=retire_commit&&(!retire_permitted||retire_generation!=captured_generation);
 // A source mutation invalidates the lease immediately, before the sticky fault.
 wire valid_source=!reset&&!stop&&!fault&&!lost&&waiting_display;
 assign lease_valid=valid_source;
 assign retire_permitted=valid_source&&reader_drained;
 assign export_permitted=!reset&&!stop&&!fault&&!lost&&!waiting_display;
 // Export COMMIT has copied geometry/raw rows to the MCU. Capture can restart,
 // but cannot replace that MCU frame until the old display lease is retired.
 // Normal retire MUST NOT release the next, possibly active, collector frame.
 assign release_frame=stop||export_release||fault||lost||bad_retire;
 always @(posedge clk)begin
  if(reset||stop)begin
   capturing<=0;waiting_display<=0;fault<=0;captured_epoch<=0;captured_generation<=0;capture_epoch<=0;capture_generation<=0;
  end else begin
   if(lost||bad_retire)fault<=1;
   if(capture_begin)begin
    if(capturing||!immutable)fault<=1;
    else begin capturing<=1;capture_epoch<=live_epoch;capture_generation<=frame_generation+16'd1;end
   end
   if(export_release)begin
    if(!export_permitted||!capturing||!frame_owned||!generation_ok)fault<=1;
    else if(commit)begin waiting_display<=1;captured_epoch<=capture_epoch;captured_generation<=capture_generation;end
   end
   if(retire_commit&&!bad_retire)waiting_display<=0;
   if(release_frame)capturing<=0;
  end
 end
endmodule
