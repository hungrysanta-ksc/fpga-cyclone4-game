// SPDX-License-Identifier: MIT
module nes_source_replace610_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,stop=0,frame_owned=1,geometry_valid=1;
 reg [15:0] frame_generation=1;
 reg source_ready=1,source_is_rom=1,source_writing=0;
 reg [31:0] captured_epoch=7,live_epoch=7;
 reg plan_valid=0;wire plan_ready;reg [1:0] plan_kind=1;
 reg [15:0] plan_generation=1;reg [9:0] plan_slot=0;reg [12:0] plan_tag=1;
 reg [47:0] plan_rows=48'o7766554433221100;
 reg [7:0] plan_mask=255,plan_alt_mask=0;reg [103:0] plan_alt_tags=0;
 reg qualified_slot=1,core_safe=1,core_request=0;reg [21:0] core_address=22'h1234;
 wire core_ready,core_response,core_error;wire [21:0] core_response_address;wire [7:0] core_data;
 reg mem_ready=1,mem_response=0,mem_error=0;reg [21:0] mem_response_address;reg [7:0] mem_data;
 wire mem_request;wire [21:0] mem_address;
 wire out_valid;reg out_ready=1;wire [7:0] out_data;wire [4:0] out_index;wire [5:0] out_length;
 wire [1:0] out_kind;wire [9:0] out_slot;wire [15:0] out_generation;wire busy,done,fault,drained;
 reg cap_start=0,cap_seal=0,cap_release=0,cap_sample=0;
 reg [15:0] cap_generation=1,cap_release_generation=1;
 reg [16:0] cap_address=0;reg [7:0] cap_data=0;wire cap_ready,cap_sample_ready;
 nes_source_tile192 #(.EXTERNAL_PLAN(1)) dut(.*);
 integer age=0,reads=0,received=0,guard=0,corrupt=0;
 reg [21:0] physical;
 function [7:0] value(input [21:0] a);value=a[7:0]^8'h91;endfunction
 always @(negedge clk)begin
  mem_response=0;
  if(age>0)begin
   age=age-1;
   if(age==0)begin
    mem_response=1;mem_ready=1;mem_response_address=physical^corrupt;mem_data=value(physical);
   end
  end
 end
 always @(posedge clk)begin
  if(mem_request&&mem_ready)begin
   if(age!=0)$fatal(1,"physical ownership");
   physical=mem_address;age=3;mem_ready<=0;reads=reads+1;
  end
 end
 task tick;begin @(posedge clk);#1;end endtask
 task fresh;begin
  reset=1;tick;reset=0;stop=0;corrupt=0;repeat(4)tick;
 end endtask
 task capture(input integer gen);integer i;begin
  cap_generation=gen;#1;if(!cap_ready)$fatal(1,"capture busy");
  cap_start=1;tick;cap_start=0;repeat(128)tick;
  for(i=16;i<32;i=i+1)begin
   cap_sample=1;cap_address=i;cap_data=value(i);#1;if(!cap_sample_ready)$fatal(1,"sample");
   tick;cap_sample=0;tick;
  end
  cap_seal=1;tick;cap_seal=0;
 end endtask
 task launch(input integer kind,tag);begin
  plan_kind=kind;plan_tag=tag;plan_slot=kind==0?1:0;plan_valid=0;guard=0;#1;
  while(!plan_ready&&guard<500)begin tick;guard=guard+1;end
  if(!plan_ready)$fatal(1,"plan timeout kind=%d tag=%d faults=%b%b%b busy=%b mem=%b tile=%d cache=%d",kind,tag,dut.denied,dut.tile_fault,dut.arbiter_fault,busy,mem_ready,dut.tile.state,dut.cache_path.cache.state);
  plan_valid=1;tick;plan_valid=0;
 end endtask
 task consume(input integer count);integer expected;begin
  received=0;guard=0;
  while(!done&&!fault&&guard<1000)begin
   if(out_valid)begin
    expected=out_index>=16?0:value(16*plan_tag+out_index/2+8*(out_index%2));
    if(out_data!==expected[7:0]||out_index!=received||out_generation!=1)$fatal(1,"data");
    received=received+1;
   end
   tick;guard=guard+1;
  end
  if(fault||!done||received!=count)$fatal(1,"tile outcome");
 end endtask
 integer prior_reads;
 initial begin
  fresh;capture(1);prior_reads=reads;launch(1,1);consume(32);
  if(reads!=prior_reads)$fatal(1,"hit requested ROM");
  launch(1,1);core_request=1;tick;core_request=0;
  if(!dut.tile_response||dut.arb_idle)$fatal(1,"hit blocked by core");
  consume(32);
  if(reads-prior_reads!=1)$fatal(1,"cached core accounting");
  prior_reads=reads;
  // Core traffic owns the physical reader while an unrelated BG fill waits.
  core_request=1;tick;core_request=0;launch(0,2);consume(16);
  if(reads-prior_reads!=17)$fatal(1,"BG/core read accounting %d",reads-prior_reads);
  // A missing OBJ line uses the same qualified reader.
  prior_reads=reads;launch(1,3);consume(32);if(reads-prior_reads!=16)$fatal(1,"miss accounting");
  // Backpressure must hold a checked byte. STOP suppresses it immediately.
  launch(1,1);out_ready=0;guard=0;
  while(!out_valid&&guard<40)begin tick;guard=guard+1;end
  if(!out_valid)$fatal(1,"no held byte");
  repeat(7)begin if(out_data!=value(16))$fatal(1,"unstable byte");tick;end
  stop=1;#1;if(out_valid)$fatal(1,"STOP output");
  tick;stop=0;out_ready=1;repeat(4)tick;
  // A stopped miss drains its physical response before another plan is admitted.
  launch(1,3);while(age==0)tick;
  stop=1;tick;if(drained)$fatal(1,"early drained");stop=0;
  repeat(8)tick;if(!drained||out_valid||done)$fatal(1,"late STOP response");
  fresh;corrupt=1;launch(0,2);guard=0;
  while(!fault&&guard<50)begin tick;guard=guard+1;end
  if(!fault||out_valid)$fatal(1,"address corruption");
  fresh;plan_generation=2;launch(1,1);repeat(3)tick;
  if(!fault||out_valid)$fatal(1,"generation");
  $display("PASS610 hit miss core STOP drain backpressure address generation");$finish;
 end
 initial begin #200000;$fatal(1,"watchdog");end
endmodule
