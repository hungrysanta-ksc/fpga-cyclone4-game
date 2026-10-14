// SPDX-License-Identifier: MIT
// Synthetic missing fetches: a separate boundary, NOT an actual-game trace.
`timescale 1ns/1ps
module level179_compact_gap_tb;
 reg clk=0,reset=1,release_scene=0,begin_scene=0,end_scene=0,event_valid=0;
 always #5 clk=~clk;
 reg [63:0] event_data=0;
 wire active,owned,valid;wire [7:0] errors,row_count,object_count,exception_count;
 wire [5:0] group_count;
 nes_native_compact_planes165 dut(.clk(clk),.reset(reset),.release_scene(release_scene),
 .begin_scene(begin_scene),.end_scene(end_scene),.source_fault(1'b0),.event_valid(event_valid),.event_data(event_data),
 .query(1'b0),.query_kind(2'd0),.query_address(11'd0),.active(active),.owned(owned),.valid(valid),.errors(errors),
 .row_count(row_count),.object_count(object_count),.exception_count(exception_count),.group_count(group_count),.response(),.hit(),.data());
 task automatic frame(input integer gap);
  @(negedge clk);release_scene=1;@(negedge clk);release_scene=0;begin_scene=1;
  @(negedge clk);begin_scene=0;
  for(integer y=0;y<224;y++)begin
   for(integer x=0;x<33;x++)begin
    // gap1: one absent tile; gap2: complete row. Neither is asserted to be
    // the exact fetch stream produced by the FPGA core's rendering disable.
    if(!((gap==1&&y==185&&x==8)||(gap==2&&y==185)))begin
     event_data=(64'(y)<<25)|(64'(x)<<33)|(64'(y&7)<<13)|64'(x);
     event_valid=1;@(negedge clk);event_valid=0;@(negedge clk);
    end
   end
   repeat(40)@(negedge clk);
  end
  end_scene=1;@(negedge clk);end_scene=0;repeat(3)@(negedge clk);
  if(!owned)$fatal(1,"did not retire");
  if(gap==0)begin
   if(!valid || errors!=0 || row_count!=224 || group_count!=28)$fatal(1,"complete/recovered frame rejected");
  end else if(valid || errors!=8'h82 || row_count!=185)$fatal(1,"missing fetch not rejected as expected %h/%d",errors,row_count);
  $display("COMPACT179 gap=%0d valid=%0d errors=%02h rows=%0d groups=%0d",gap,valid,errors,row_count,group_count);
 endtask
 initial begin
  repeat(3)@(negedge clk);reset=0;
  frame(0);frame(1);frame(0);frame(2);frame(0);
  $display("PASS COMPACT179 cases=5");$finish;
 end
 initial begin #10000000;$fatal(1,"watchdog");end
endmodule
