// SPDX-License-Identifier: MIT
// Experimental CF85: reciprocal clock liveness, NOT frequency/voltage sensing.
// Conditional guarantee requires one clock to continue. Both stopped is unsafe.
// Intended clocks: memory 8MHz, reference SNES_SYSCLK 20..22MHz. Board availability,
// CDC placement, routed asynchronous shutdown and external timing are NOT signed off.
module nes_diag_clock_guard085(
 input wire mem_clk,ref_clk,reset,
 output wire allow_memory,output wire fault
);
 reg mem_heartbeat=0;
 reg [3:0] ref_divider=0;
 always @(posedge mem_clk or posedge reset)
  if(reset)mem_heartbeat<=0;else mem_heartbeat<=!mem_heartbeat;
 always @(posedge ref_clk or posedge reset)
  if(reset)ref_divider<=0;else ref_divider<=ref_divider+1'b1;

 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
 reg [1:0] mem_sync=0,ref_sync=0;
 always @(posedge ref_clk or posedge reset)
  if(reset)mem_sync<=0;else mem_sync<={mem_sync[0],mem_heartbeat};
 always @(posedge mem_clk or posedge reset)
  if(reset)ref_sync<=0;else ref_sync<={ref_sync[0],ref_divider[3]};

 reg mem_seen=0,ref_seen=0;
 reg [5:0] ref_age=0;
 reg [4:0] mem_age=0;
 reg [3:0] ref_edges=0,mem_edges=0;
 reg ref_qualified=0,mem_qualified=0;
 reg ref_fault=0,mem_fault=0;
 // Faults latch until raw lock loss/reconfiguration; resumed clocks alone must
 // not re-arm an image after a truncated write. Guard reset excludes its own fault.
 always @(posedge ref_clk or posedge reset)begin
  if(reset)begin
   mem_seen<=0;ref_age<=0;ref_edges<=0;ref_qualified<=0;ref_fault<=0;
  end else if(!ref_fault)begin
   if(mem_sync[1]!=mem_seen)begin
    mem_seen<=mem_sync[1];ref_age<=0;
    if(!ref_qualified)begin
     if(ref_edges==7)ref_qualified<=1;else ref_edges<=ref_edges+1'b1;
    end
   end else if(ref_age==63)ref_fault<=1;
   else ref_age<=ref_age+1'b1;
  end
 end
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin
   ref_seen<=0;mem_age<=0;mem_edges<=0;mem_qualified<=0;mem_fault<=0;
  end else if(!mem_fault)begin
   if(ref_sync[1]!=ref_seen)begin
    ref_seen<=ref_sync[1];mem_age<=0;
    if(!mem_qualified)begin
     if(mem_edges==7)mem_qualified<=1;else mem_edges<=mem_edges+1'b1;
    end
   end else if(mem_age==31)mem_fault<=1;
   else mem_age<=mem_age+1'b1;
  end
 end
 assign fault=ref_fault||mem_fault;
 // This only asserts the existing asynchronous reset. Its release passes through
 // memory_release plus the unchanged 1600-cycle startup guard in the consumer.
 assign allow_memory=!reset&&ref_qualified&&mem_qualified&&!fault;
endmodule
