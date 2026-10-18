// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module source_query235_guards_tb;
 reg clk=0;always #22.727 clk=~clk;
 reg reset=1,abort_source=0,start=0,frame_owned=1,geometry_valid=1;
 reg [15:0] generation=16'hffff;reg [2:0] patches=0;
 reg [7:0] rows=224,objects=1,exceptions=1;reg [5:0] groups=1,palettes=1;
 wire start_ready,query,out_valid,done;wire [2:0] kind;wire [12:0] index,offset;wire [15:0] query_generation;
 reg response=0,hit=1,out_ready=1,respond=1;reg [63:0] data=0;
 wire [7:0] out_data;wire [3:0] fault;integer bad_kind=-1,checks=0,n;reg [7:0] held;reg [12:0] held_offset;
 nes_source_query235 dut(.clk(clk),.reset(reset),.abort_source(abort_source),.start(start),.start_ready(start_ready),
 .frame_owned(frame_owned),.geometry_valid(geometry_valid),.frame_generation(generation),.patch_count(patches),
 .row_count(rows),.object_count(objects),.exception_count(exceptions),.group_count(groups),.palette_count(palettes),
 .query(query),.query_kind(kind),.query_index(index),.query_generation(query_generation),.response(response),.hit(hit),.data(data),
 .out_valid(out_valid),.out_ready(out_ready),.out_data(out_data),.out_offset(offset),.done(done),.fault(fault));
 always @(posedge clk)begin
  response<=query&&respond;data<=(kind==bad_kind)?64'h8000000000000000:0;
 end
 task fresh;begin
  @(negedge clk);reset=1;abort_source=0;start=0;frame_owned=1;geometry_valid=1;generation=16'hffff;
  rows=224;objects=1;exceptions=1;groups=1;palettes=1;out_ready=1;respond=1;hit=1;bad_kind=-1;
  repeat(2)@(negedge clk);reset=0;
 end endtask
 task launch;begin @(negedge clk);start=1;@(negedge clk);start=0;end endtask
 task expect_fault(input [3:0] code);begin
  repeat(5)@(negedge clk);
  if(fault!=code||query||out_valid||start_ready||done)$fatal(1,"fault gate %0d/%0d",fault,code);
  launch;if(fault!=code||start_ready)$fatal(1,"fault restart");checks++;
 end endtask
 initial begin
  for(n=0;n<9;n++)begin fresh;
   case(n)0:rows=223;1:groups=0;2:groups=33;3:objects=129;4:exceptions=129;5:palettes=0;6:palettes=3;7:frame_owned=0;8:geometry_valid=0;endcase
   launch;expect_fault(1);
  end
  for(n=0;n<6;n++)if(n!=2)begin fresh;bad_kind=n;launch;wait(fault);expect_fault(3);end
  fresh;hit=0;launch;wait(fault);expect_fault(3);
  fresh;respond=0;launch;repeat(40)@(negedge clk);
  if(out_valid||done||fault)$fatal(1,"fabricated missing response");abort_source=1;expect_fault(4);
  fresh;out_ready=0;launch;wait(out_valid);@(negedge clk);held=out_data;held_offset=offset;
  repeat(50)begin @(negedge clk);if(!out_valid||out_data!=held||offset!=held_offset||query)$fatal(1,"backpressure unstable");end checks++;
  generation=0;expect_fault(2);
  fresh;launch;wait(out_valid);@(negedge clk);frame_owned=0;expect_fault(2);
  fresh;out_ready=0;launch;wait(out_valid);@(negedge clk);abort_source=1;expect_fault(4);
  fresh;launch;wait(out_valid);@(negedge clk);reset=1;#1;if(out_valid||query)$fatal(1,"reset gate");
  fresh;generation=0;launch;wait(done);@(negedge clk);if(fault||offset!=5740)$fatal(1,"fresh zero generation");checks++;
  $display("PASS QUERY235 GUARDS checks=%0d",checks);$finish;
 end
 initial begin #20000000;$fatal(1,"watchdog");end
endmodule
