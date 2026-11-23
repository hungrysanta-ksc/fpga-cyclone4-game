// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module tb_nes_companion952 #(parameter CROSS=0);
 localparam [16:0] FIRST=CROSS ? 17'd100096 : 17'd99904;
 reg clk=0,reset=1,flush=1,kill=1,hint=0,demand=0,allow=1;
 reg done=0, bad=0, changed=0;
 reg [21:0] address=0,back=0;
 wire ready,response,request;
 wire [21:0] physical;
 wire [7:0] lo,hi;
 always #5 clk=~clk;
 function automatic [7:0] low(input [21:0] a,input salt);
  return a[7:0]^a[15:8]^(salt?8'hb9:8'h30);
 endfunction
 nes_e9_rows914 #(.COMPACT(1),.CHECK_HINT(1),.SINGLE_READ(1),.COMPLETE_ROW_SET(1)) dut(
  .clk(clk),.reset(reset),.invalidate(kill),.flush_rom(flush),.empty_capture(1'b1),
  .hint(hint),.tag(CROSS ? 13'd6254 : 13'd6255),.mask(CROSS ? 8'h7f : 8'hc0),.demand(demand),.pair(1'b1),.address(address),
  .ready(ready),.response(response),.lo(lo),.hi(hi),.request(request),.physical_address(physical),
  .grant_ready(allow),.reply(done&&!kill),.physical_done(done),.physical_error(bad),.reply_address(back),
  .physical_lo(low(back,changed)),.physical_hi(~low(back,changed)));
 integer reads=0,aux=0;
 reg fail_row=0;
 always @(posedge clk)begin
  done<=request&&allow;
  if(request&&allow)begin
   reads<=reads+1; back<=physical;
   bad<=dut.aux952 && fail_row && physical[16:0]==FIRST+3;
   if(dut.aux952)aux<=aux+1;
  end
 end
 task automatic demand_row(input [16:0] a,input must_hit);
  integer before_reads;
  @(negedge clk); before_reads=reads;address={5'h10,a};demand=1;
  do @(posedge clk);while(!ready);
  @(negedge clk);demand=0;
  while(!response)@(negedge clk);
  if(reads!=before_reads+!must_hit || lo!==low(address,changed)||hi!==~low(address,changed))
   $fatal(1,"row %d grants %d expected hit %d",a,reads-before_reads,must_hit);
 endtask
 task automatic arm_hint;
  demand_row(17'd117,0);
  @(negedge clk);hint=1;@(negedge clk);hint=0;
  wait(dut.aux952);
 endtask
 task automatic scrub;
  kill=1;flush=1;repeat(3)@(negedge clk);kill=0;flush=0;repeat(265)@(negedge clk);
 endtask
 initial begin
  repeat(4)@(negedge clk);reset=0;scrub();
  arm_hint(); @(posedge clk);@(negedge clk);kill=1;flush=1;changed=1;
  #1;if(request||response)$fatal(1,"STOP exposed response or request");
  scrub();demand_row(FIRST,0);scrub();
  fail_row=1;arm_hint();allow=0;
  repeat(3)@(negedge clk);
  if(!dut.aux952||physical[16:0]!=FIRST)$fatal(1,"first grant moved under backpressure");
  allow=1;
  for(int i=0;i<16;i++)begin
   do @(posedge clk);while(!dut.aux952||!allow);
   if(physical[16:0]!==FIRST+16*(i/8)+i%8)$fatal(1,"wrong order %d",i);
  end
  repeat(3)@(negedge clk);kill=1;repeat(4)@(negedge clk);kill=0;
  for(int i=0;i<16;i++)demand_row(FIRST+16*(i/8)+i%8,i!=3);
  if(aux!=17)$fatal(1,"unexpected extra requests");
  $display("PASS952 16 actual grants, failed reply, two planes, lease, STOP drain and changed ROM");$finish;
 end
 initial begin #40000;$fatal(1,"timeout grants %d, cursor %d",reads,dut.cursor952);end
endmodule
