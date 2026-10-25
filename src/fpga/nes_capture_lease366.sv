// SPDX-License-Identifier: MIT
// Collector READ completion releases capture RAM. ARM input COMMIT separately
// opens the display lease. The sealed local source context survives a following
// capture and is invalidated immediately by STOP or immutable-ROM loss.
module nes_capture_lease366(
 input wire clk,reset,stop,capture_begin,frame_owned,geometry_valid,
 input wire [15:0] frame_generation,
 input wire materialize366,export_release,input wire [3:0] export_error,
 input wire source_ready,source_is_rom,source_writing,input wire [31:0] live_epoch,
 input wire reader_drained,retire_commit,input wire [15:0] retire_generation,
 output wire release_frame,lease_valid,retire_permitted,export_permitted,
 output reg [31:0] captured_epoch,output reg [15:0] captured_generation,
 output reg waiting_display,fault,
 output wire input_ready365,output wire [31:0] input_epoch365,output wire [15:0] input_generation365,
 output wire local_source366
);
 reg capturing,materialized;reg [31:0] capture_epoch;reg [15:0] capture_generation;
 wire immutable=source_ready&&source_is_rom&&!source_writing;
 wire capture_ok=immutable&&capture_epoch==live_epoch;
 wire generation_ok=frame_generation==capture_generation;
 wire lost=(capturing&&(!capture_ok||(frame_owned&&!generation_ok)))||
           (materialized&&(!immutable||captured_epoch!=live_epoch));
 wire bad_retire=retire_commit&&(!retire_permitted||retire_generation!=captured_generation);
 assign local_source366=!reset&&!stop&&!fault&&!lost&&materialized;
 assign lease_valid=local_source366&&waiting_display;
 assign retire_permitted=lease_valid&&reader_drained;
 assign export_permitted=!reset&&!stop&&!fault&&!lost&&!waiting_display&&!materialized;
 assign input_epoch365=capture_epoch;assign input_generation365=capture_generation;
 assign input_ready365=capturing&&frame_owned&&geometry_valid&&capture_ok&&generation_ok&&export_permitted&&live_epoch!=0;
 // Input ACK and display retirement never release a following collector frame.
 assign release_frame=stop||materialize366||fault||lost||bad_retire;
 always @(posedge clk)begin
  if(reset||stop)begin
   capturing<=0;materialized<=0;waiting_display<=0;fault<=0;
   captured_epoch<=0;captured_generation<=0;capture_epoch<=0;capture_generation<=0;
  end else begin
   if(lost||bad_retire)fault<=1;
   if(capture_begin)begin
    if(capturing||!immutable)fault<=1;
    else begin capturing<=1;capture_epoch<=live_epoch;capture_generation<=frame_generation+16'd1;end
   end
   if(materialize366)begin
    if(!input_ready365||materialized||export_error!=0)fault<=1;
    else begin materialized<=1;captured_epoch<=capture_epoch;captured_generation<=capture_generation;end
   end
   if(export_release)begin
    if(!local_source366||waiting_display||export_error!=0)fault<=1;
    else waiting_display<=1;
   end
   if(retire_commit&&!bad_retire)begin waiting_display<=0;materialized<=0;end
   if(release_frame)capturing<=0;
  end
 end
endmodule
