// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module capture201_faults_tb;
 reg clk=0;always #5 clk=!clk;
 reg reset=1,stop=0,capture_begin=0,frame_owned=0,geometry_valid=0,export_release=0;
 reg [15:0] frame_generation=0,retire_generation=0;reg [3:0] export_error=0;
 reg source_ready=1,source_is_rom=1,source_writing=0,reader_drained=1,retire_commit=0;
 reg [31:0] live_epoch=100;
 wire release_frame,lease_valid,retire_permitted,export_permitted,waiting_display,fault;
 wire [31:0] captured_epoch;wire [15:0] captured_generation;
 nes_capture_lease201 dut(.*);
 integer checks=0;
 task tick;@(posedge clk);#1;@(negedge clk);endtask
 task clear;
  begin reset=1;stop=0;capture_begin=0;frame_owned=0;geometry_valid=0;export_release=0;export_error=0;
   source_ready=1;source_is_rom=1;source_writing=0;reader_drained=1;retire_commit=0;live_epoch=100;frame_generation=0;
   tick();reset=0;tick();end
 endtask
 task start;
  begin capture_begin=1;tick();capture_begin=0;frame_generation=frame_generation+16'd1;tick();end
 endtask
 task seal;
  begin frame_owned=1;geometry_valid=1;tick();if(fault)$fatal(1,"seal admission");end
 endtask
 task exported;
  begin
   if(!export_permitted)$fatal(1,"export blocked");
   export_release=1;tick();export_release=0;frame_owned=0;geometry_valid=0;tick();
   if(!waiting_display||!lease_valid||release_frame||export_permitted)$fatal(1,"COMMIT source ownership");
  end
 endtask
 task expect_fault;
  begin tick();if(!fault||lease_valid||!release_frame)$fatal(1,"fault did not cancel");checks++;end
 endtask
 initial begin
  clear();frame_generation=16'hffff;start();seal();exported();
  if(captured_generation!==0||captured_epoch!==100)$fatal(1,"capture wrap");checks++;
  reader_drained=0;tick();if(retire_permitted)$fatal(1,"pending read admitted retire");checks++;
  reader_drained=1;retire_generation=0;retire_commit=1;#1;if(release_frame)$fatal(1,"retire touched collector");tick();retire_commit=0;
  frame_owned=0;geometry_valid=0;tick();if(waiting_display||fault||lease_valid)$fatal(1,"retire terminal");checks++;
  // Reuse a changed source epoch only between captures, not while retaining one.
  live_epoch=101;start();seal();exported();if(captured_epoch!=101)$fatal(1,"new epoch");checks++;
  // Capture another generation without replacing the MCU/ROM source lease.
  start();seal();if(captured_generation!=1||export_permitted||!lease_valid)$fatal(1,"overlap lease");checks++;
  retire_generation=1;retire_commit=1;tick();retire_commit=0;#1;
  if(release_frame||!frame_owned||lease_valid||!export_permitted)$fatal(1,"retire discarded next capture");checks++;
  exported();if(captured_generation!=2)$fatal(1,"next exported generation");checks++;
  clear();start();live_epoch=101;expect_fault();
  clear();start();source_writing=1;expect_fault();
  clear();start();source_ready=0;expect_fault();
  clear();start();source_is_rom=0;expect_fault();
  clear();source_writing=1;start();expect_fault();
  clear();source_is_rom=0;start();expect_fault();
  clear();source_ready=0;start();expect_fault();
  clear();start();seal();frame_generation=2;expect_fault();
  clear();start();seal();exported();retire_generation=2;retire_commit=1;expect_fault();
  clear();start();seal();retire_generation=1;retire_commit=1;expect_fault();
  clear();start();seal();exported();start();seal();export_release=1;expect_fault();
  clear();start();capture_begin=1;expect_fault();
  clear();start();frame_owned=1;geometry_valid=0;export_release=1;tick();export_release=0;frame_owned=0;tick();
  if(fault||waiting_display||lease_valid)$fatal(1,"invalid capture not discarded");checks++;
  start();seal();export_error=6;export_release=1;tick();export_release=0;frame_owned=0;tick();
  if(fault||waiting_display||lease_valid)$fatal(1,"negative exporter ACK held");checks++;
  clear();start();seal();exported();stop=1;#1;if(!release_frame||lease_valid||retire_permitted)$fatal(1,"STOP gate");tick();
  stop=0;frame_owned=0;geometry_valid=0;tick();start();seal();exported();checks++;
  clear();start();seal();exported();live_epoch=101;#1;if(lease_valid||retire_permitted)$fatal(1,"mutation delayed until edge");expect_fault();
  $display("PASS CAPTURE201FAULT checks=%0d",checks);$finish;
 end
 initial begin #100000;$fatal(1,"watchdog");end
endmodule
