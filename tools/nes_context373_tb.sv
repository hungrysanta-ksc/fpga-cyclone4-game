// SPDX-License-Identifier: MIT
// Deliberate collector stub: unit tests admission/retirement, not PPU semantics.
module nes_native_frame201 #(parameter REQUIRED_BITMAP=1)(input wire clk,reset,release_frame,rom_fault,ppu_ce,input wire [8:0] dot,
 output wire capture_begin,output reg owned,geometry_valid,output reg [15:0] generation);
 assign capture_begin=ppu_ce&&dot==0&&!owned&&!rom_fault;
 always @(posedge clk)if(reset)begin owned<=0;geometry_valid<=0;generation<=0;end
 else if(release_frame)begin owned<=0;geometry_valid<=0;end
 else if(capture_begin)begin owned<=1;geometry_valid<=1;generation<=generation+1'b1;end
endmodule
module context373_tb;
 parameter CASE=0;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,stop=0,source_done=0,identity_ready=0,display_ack=0,retire_commit=0,capture_materialized366=0;
 reg source_writing=0,ppu_ce=0;reg [8:0] dot=0;
 reg [31:0] live_epoch=32'h1234;reg [15:0] retire_generation=1;
 wire source_start,identity_valid,prelease,source_owned365,lease_valid,waiting_display,lease_fault,owned,geometry_valid;
 wire [31:0] source_epoch,source_serial,captured_epoch,display_serial373;
 wire [15:0] source_generation,captured_generation;wire [2:0] display_raw373;
 nes_native_capture365 #(.EARLY_RELEASE(1)) dut(.clk(clk),.reset(reset),.stop(stop),.source_start_ready(1'b1),.source_done(source_done),
 .identity_ready(identity_ready),.display_ack(display_ack),.source_ready(1'b1),.source_is_rom(1'b1),.source_writing(source_writing),.live_epoch(live_epoch),
 .export_error(4'd0),.flow_error(1'b0),.reader_drained(1'b1),.retire_commit(retire_commit),.retire_generation(retire_generation),
 .capture_materialized366(capture_materialized366),.source_start(source_start),.identity_valid(identity_valid),.prelease(prelease),.source_owned365(source_owned365),
 .source_epoch(source_epoch),.source_serial(source_serial),.source_generation(source_generation),.lease_valid(lease_valid),.waiting_display(waiting_display),.lease_fault(lease_fault),
 .captured_epoch(captured_epoch),.captured_generation(captured_generation),.display_serial373(display_serial373),.display_raw373(display_raw373),
 .ppu_ce(ppu_ce),.rom_fault(1'b0),.dot(dot),.owned(owned),.geometry_valid(geometry_valid),.patch_count());
 // Three raw groups are stable at capture admission, independent of display.
 initial force dut.patch_count=3;
 task tick;begin @(negedge clk);end endtask
 task capture;begin tick();ppu_ce=1;tick();ppu_ce=0;wait(dut.started);tick();end endtask
 task materialize;begin capture_materialized366=1;tick();capture_materialized366=0;tick();if(owned)$fatal(1,"collector not released");end endtask
 task commit_input;begin source_done=1;tick();source_done=0;
  if(!waiting_display&&!prelease)$fatal(1,"hint lease gap after input ACK373");
  repeat(3)tick();end endtask
 initial begin
  repeat(3)tick();reset=0;capture();
  if(CASE==3)begin source_done=1;tick();source_done=0;end
  else begin
   materialize();commit_input();
   if(!lease_valid||display_serial373!=1||captured_generation!=1||display_raw373!=3)$fatal(1,"first display context");
   identity_ready=1;tick();identity_ready=0;
   capture();materialize();
   if(!lease_valid||display_serial373!=1||source_serial!=2||captured_generation!=1||source_generation!=2)$fatal(1,"input/display alias");
   if(CASE==1)begin retire_generation=2;display_ack=1;retire_commit=1;tick();display_ack=0;retire_commit=0;end
   else if(CASE==2)begin live_epoch=32'h5678;tick();end
   else if(CASE==4)begin stop=1;tick();stop=0;end
   else begin
    commit_input();if(!dut.committed||display_serial373!=1)$fatal(1,"pending input lost");
    display_ack=1;retire_commit=1;tick();display_ack=0;retire_commit=0;repeat(3)tick();
    if(!lease_valid||display_serial373!=2||captured_generation!=2)$fatal(1,"ACK cleared next input");
    retire_generation=2;identity_ready=1;tick();identity_ready=0;
    display_ack=1;retire_commit=1;tick();display_ack=0;retire_commit=0;tick();
    if(lease_valid||waiting_display||lease_fault)$fatal(1,"second final ACK");
    stop=1;tick();stop=0;
   end
  end
  repeat(3)tick();source_done=1;capture_materialized366=1;repeat(2)tick();source_done=0;capture_materialized366=0;repeat(3)tick();
  if(lease_valid||identity_valid||source_start||source_owned365)$fatal(1,"late DONE after fault/STOP");
  if(CASE!=0&&CASE!=4&&!lease_fault)$fatal(1,"missing ownership fault");
  $display("PASS CONTEXT373 case=%0d",CASE);$finish;
 end
 initial begin #100000;$fatal(1,"context timeout");end
endmodule

