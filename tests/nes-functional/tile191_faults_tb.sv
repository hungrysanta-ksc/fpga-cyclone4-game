// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module tile191_faults_tb;
 reg clk=0,reset=1,stop=0,lease=1,pv=0,idle=1;
 always #5.952 clk=!clk;
 reg [15:0] pg=12;reg [1:0] pk=0;reg [9:0] ps=1;
 wire pr,req,cancel,busy,fault,done,ov;wire [16:0] addr;wire [15:0] mg;
 reg mr=0,me=0;reg [16:0] ra=0;reg [15:0] rg=12;
 wire [7:0] od;wire [4:0] oi;wire [5:0] ol;wire [1:0] ok;wire [9:0] os;wire [15:0] og;
 integer mode,n,checks=0;
 nes_tile191 #(.MAX_CYCLES(128)) dut(.clk(clk),.reset(reset),.stop(stop),.lease_valid(lease),.lease_generation(16'd12),
  .plan_valid(pv),.plan_ready(pr),.plan_kind(pk),.plan_generation(pg),.plan_slot(ps),.plan_tag(13'd3),
  .plan_rows(48'd0),.plan_mask(8'hff),.plan_alt_mask(8'd0),.plan_alt_tags(104'd0),
  .mem_idle(idle),.mem_ready(1'b1),.mem_request(req),.mem_cancel(cancel),.mem_address(addr),.mem_generation(mg),
  .mem_response(mr),.mem_error(me),.response_address(ra),.response_generation(rg),.response_data(8'h5a),
  .out_valid(ov),.out_ready(1'b0),.out_data(od),.out_index(oi),.out_length(ol),.out_kind(ok),.out_slot(os),.out_generation(og),
  .busy(busy),.fault(fault),.done(done));
 task tick;begin @(posedge clk);#1;end endtask
 task fresh;begin
  @(negedge clk);reset=1;stop=0;lease=1;pv=0;idle=1;mr=0;me=0;pg=12;pk=0;ps=1;tick();
  @(negedge clk);reset=0;tick();
 end endtask
 task start;begin @(negedge clk);pv=1;tick();@(negedge clk);pv=0;end endtask
 initial begin
  for(mode=0;mode<7;mode=mode+1)begin
   fresh();if(mode==0)pg=13;if(mode==1)begin pk=1;ps=128;end
   start();
   if(mode>=2)begin
    wait(req);@(posedge clk);#1;
    @(negedge clk);ra=addr;rg=mg;
    if(mode==2)begin rg=13;mr=1;end
    if(mode==3)begin ra=addr^1;mr=1;end
    if(mode==4)begin me=1;mr=1;end
    if(mode==6)lease=0;
   end
   for(n=0;n<140&&!fault;n=n+1)begin tick();if(ov||done)$fatal(1,"invalid tile visible mode=%d",mode);end
   if(!fault||!cancel)$fatal(1,"missing bounded fault mode=%d",mode);checks=checks+1;
  end
  fresh();start();wait(req);tick();@(negedge clk);idle=0;stop=1;tick();
  if(busy||ov||!cancel)$fatal(1,"STOP did not cancel");
  @(negedge clk);stop=0;pv=1;
  repeat(3)begin tick();if(pr||busy)$fatal(1,"restart before flush");end
  @(negedge clk);mr=1;ra=addr;rg=12;
  tick();if(pr||busy)$fatal(1,"stale reply admitted");
  @(negedge clk);mr=0;idle=1;#1;if(!pr)$fatal(1,"flush never reopened");
  tick();if(!busy)$fatal(1,"fresh command not accepted");checks=checks+1;
  fresh();start();
  // Complete a tile but keep the output blocked, then revoke its lease.
  for(n=0;n<16;n=n+1)begin
   wait(req);tick();@(negedge clk);ra=addr;rg=mg;mr=1;tick();@(negedge clk);mr=0;
  end
  wait(ov);@(negedge clk);lease=0;#1;if(ov)$fatal(1,"revoked tile still visible");
  tick();if(!fault||done)$fatal(1,"revoked output accepted");checks=checks+1;
  $display("PASS TILE191FAULT cases=%0d",checks);$finish;
 end
 initial begin #1000000;$fatal(1,"fault watchdog");end
endmodule
