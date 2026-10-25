// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module nes_query355_tb;
 parameter real PHASE=0;
 reg h=0,n=0,run_h=1,run_n=1;
 always #5.952 if(run_h)h=~h;
 initial begin #(PHASE);forever #22.727 if(run_n)n=~n;end
 reg reset=1,stop=0,begin_frame=0,req_valid=0,rsp_ready=1;
 reg [31:0] req_data=0;wire req_ready,rsp_valid,drained,active;wire [64:0] rsp_data;
 wire query;wire [31:0] query_data;
 reg response=0,response_hit=0;reg [63:0] response_data=0;
 reg display_phase=0,plan_zero=0,plan_step=0;wire [9:0] plan_cursor;wire owner_fault;
 nes_query355 dut(h,n,reset,stop,begin_frame,drained,active,req_valid,req_ready,req_data,rsp_valid,rsp_ready,rsp_data,query,query_data,response,response_hit,response_data,display_phase,plan_zero,plan_step,plan_cursor,owner_fault);
 integer queries=0,consumed=0,cases=0;reg hold_response=0,pending=0;reg [63:0] captured;reg [31:0] salt=0;
 function [63:0] data(input [31:0] v);data={v^32'h12345678^salt,~v^salt};endfunction
 always @(posedge n)begin
  response<=0;
  if(reset)begin pending<=0;end
  else begin
   if(!pending&&!query)response_data<=response_data^64'h5a5aa5a55a5aa5a5;
   if(query)begin
    if(pending)$fatal(1,"duplicate query");captured<=data(query_data);queries<=queries+1;
    if(hold_response)pending<=1;
    else begin response<=1;response_hit<=1;response_data<=data(query_data);end
   end
   if(pending&&!hold_response)begin response<=1;response_hit<=1;response_data<=captured;pending<=0;end
  end
 end
 always @(posedge h)if(!reset&&rsp_valid&&rsp_ready)consumed<=consumed+1;
 task start_frame;
 begin
  wait(drained);@(negedge h);salt=salt+1;begin_frame=1;@(negedge h);begin_frame=0;wait(active);
 end endtask
 task cancel_frame;
 begin @(negedge h);stop=1;@(negedge h);stop=0;end endtask
 task request(input [31:0] value);
 begin wait(req_ready);@(negedge h);req_valid=1;req_data=value;@(negedge h);req_valid=0;end endtask
 task normal(input [31:0] value);
 integer before_count;time t0;
 begin
  before_count=consumed;rsp_ready=0;t0=$time;request(value);req_data=~value;wait(rsp_valid);
  if(rsp_data!=={1'b1,data(value)})$fatal(1,"response mismatch");
  repeat(9)begin @(negedge h);if(!rsp_valid||rsp_data!=={1'b1,data(value)})$fatal(1,"unstable held response");end
  $display("LATENCY value=%h ns=%0t",value,$time-t0);
  rsp_ready=1;@(negedge h);wait(consumed==before_count+1);cases=cases+1;
 end endtask
 time accepted_time;reg response_seen=0;
 always @(posedge h)if(!reset)begin
  if(req_valid&&req_ready)begin accepted_time=$time;response_seen=0;end
  if(rsp_valid&&!response_seen)begin $display("READY_LATENCY ns=%0t",$time-accepted_time);response_seen=1;end
 end
 integer k,before_count;reg [9:0] saved;
 initial begin
  #200;reset=0;start_frame();
  for(k=0;k<12;k=k+1)normal(32'h10001000+k);
  // STOP has priority over same-edge request admission and response publish.
  before_count=queries;@(negedge h);stop=1;req_valid=1;req_data=32'h11110001;
  @(negedge h);stop=0;req_valid=0;wait(drained);if(queries!=before_count)$fatal(1,"STOP admitted request");
  start_frame();normal(32'h11110001);cases=cases+1;
  rsp_ready=0;before_count=consumed;request(32'h11110002);wait(rsp_valid);@(negedge h);stop=1;rsp_ready=1;
  @(negedge h);stop=0;wait(drained);if(consumed!=before_count)$fatal(1,"STOP published response");
  start_frame();normal(32'h11110002);cases=cases+1;
  // Cancel at each host edge through request synchronization and response.
  for(k=0;k<32;k=k+1)begin
   rsp_ready=0;before_count=consumed;request(32'h22220000+k);repeat(k)@(negedge h);cancel_frame();
   wait(drained);if(consumed!=before_count||rsp_valid||active)$fatal(1,"cancel published");
   // Identical generation/index after STOP must receive only its new response.
   start_frame();normal(32'h22220000+k);cases=cases+1;
  end
  // Collector delayed across STOP: restart prohibited until late response drains.
  hold_response=1;rsp_ready=0;request(32'h33330001);wait(pending);cancel_frame();
  req_valid=1;req_data=32'hdead0001;begin_frame=1;
  repeat(30)begin @(negedge h);if(drained||rsp_valid||active||req_ready)$fatal(1,"early drain");end
  req_valid=0;begin_frame=0;
  hold_response=0;wait(drained);start_frame();normal(32'h33330001);cases=cases+1;
  // NES clock stopped while a request is in flight.
  hold_response=1;request(32'h44440001);wait(pending);@(negedge n);run_n=0;cancel_frame();
  repeat(30)begin @(negedge h);if(drained||rsp_valid)$fatal(1,"paused NES restart");end
  run_n=1;hold_response=0;wait(drained);start_frame();normal(32'h44440001);cases=cases+1;
  // Host clock pause while collector reply returns.
  rsp_ready=0;request(32'h55550001);@(negedge h);run_h=0;repeat(12)@(negedge n);run_h=1;
  wait(rsp_valid);if(rsp_data!=={1'b1,data(32'h55550001)})$fatal(1,"paused host reply");cancel_frame();wait(drained);start_frame();cases=cases+1;
  // A phase change cannot overlap a query already owned by the NES side.
  hold_response=1;rsp_ready=0;request(32'h55550002);wait(pending);@(negedge n);display_phase=1;plan_step=1;
  repeat(4)@(negedge n);if(!owner_fault||plan_cursor!=0)$fatal(1,"query/plan owner overlap");
  plan_step=0;hold_response=0;wait(rsp_valid);if(rsp_data[64])$fatal(1,"overlap response accepted");
  cancel_frame();wait(drained);display_phase=0;start_frame();normal(32'h55550002);cases=cases+1;
  // Plan cursor belongs to NES, independent of host clock and query control.
  wait(dut.port_idle);@(negedge n);display_phase=1;plan_zero=1;@(negedge n);plan_zero=0;run_h=0;plan_step=1;
  repeat(1031)@(negedge n);plan_step=0;if(plan_cursor!=7)$fatal(1,"plan wrap");
  run_h=1;saved=plan_cursor;repeat(9)@(negedge n);if(plan_cursor!=saved)$fatal(1,"cursor drift");cases=cases+1;
  // Query cannot consume the plan-owned phase.
  rsp_ready=0;request(32'h66660001);wait(rsp_valid);if(rsp_data!=0||!owner_fault)$fatal(1,"owner violation");cancel_frame();wait(drained);
  if(plan_cursor!=0)$fatal(1,"STOP cursor");display_phase=0;start_frame();normal(32'h77770001);cases=cases+1;
  @(negedge n);plan_step=1;@(negedge n);plan_step=0;if(!owner_fault||plan_cursor!=0)$fatal(1,"input plan step");cancel_frame();wait(drained);cases=cases+1;
  start_frame();hold_response=1;request(32'h88880001);wait(pending);@(negedge h);run_h=0;reset=1;
  #100;if(active||rsp_valid||plan_cursor!=0)$fatal(1,"async common reset");run_h=1;hold_response=0;#100;reset=0;
  start_frame();normal(32'h88880001);cases=cases+1;
  $display("PASS QUERY355 phase=%0f cases=%0d queries=%0d consumed=%0d",PHASE,cases,queries,consumed);$finish;
 end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
