// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module lifetime374_tb;
 parameter CASE=0;
 reg h=0,n=0,reset=1,stop=0,wv=0,seal=0,retire=0,permit=0,pr=0,tdone=0,er=0;
 always #5.952381 h=~h;always #22.727273 n=~n;
 reg [7:0] wd;reg [9:0] length;reg [4:0] plans;reg [15:0] gen=1;
 wire wr,idle,fault,pv,ev,partial,retired,retire_done;
 wire [1:0] kind;wire [15:0] pg;wire [9:0] slot;wire [12:0] tag;wire [47:0] rows;wire [7:0] mask,am;wire [103:0] tags;
 nes_plan_batch206 #(.SHARED_CRC307(1)) dut(.host_clk(h),.nes_clk(n),.reset(reset),.active(1'b1),.stop(stop),.source_fault(1'b0),
 .write_valid(wv),.write_ready(wr),.write_data(wd),.retire(retire),.retire_done(retire_done),.retire_permitted(permit),.retire_commit(retired),
 .seal(seal),.seal_length(length),.seal_plans(plans),.seal_crc(16'd0),.host_idle(idle),.fault(fault),.lease_valid(1'b1),.lease_generation(gen),
 .plan_valid(pv),.plan_ready(pr),.tile_done(tdone),.plan_kind(kind),.plan_generation(pg),.plan_slot(slot),.plan_tag(tag),.plan_rows(rows),.plan_mask(mask),.plan_alt_mask(am),.plan_alt_tags(tags),
 .end_valid(ev),.end_partial295(partial),.end_ready(er));
 integer retired_count=0;
 always @(posedge n)if(!reset&&retired)retired_count++;
 task byte374(input [7:0] b);
 begin wait(wr);@(negedge h);wd=b;wv=1;@(negedge h);wv=0;repeat(32)@(negedge h);end endtask
 task batch374(input integer which);
 begin
  byte374(which==1?8'h81:8'h80);byte374(gen[7:0]);byte374(gen[15:8]);
  byte374(which+1);byte374(0);byte374(8'h40+which);byte374(0);if(which==1)byte374(8'h35);
  byte374(which==0?8'h87:8'h83);byte374(gen[7:0]);byte374(gen[15:8]);
  @(negedge h);length=which==1?11:10;plans=2;seal=1;@(negedge h);seal=0;
 end endtask
 task consume374;
 begin
  @(negedge n);pr=1;@(negedge n);pr=0;repeat(3)@(negedge n);tdone=1;@(negedge n);tdone=0;
 end endtask
 task end374(input bit expected_partial);
 begin wait(ev);if(partial!=expected_partial)$fatal(1,"partial/frame end alias");@(negedge n);er=1;@(negedge n);er=0;end endtask
 task bad374;
 begin
  wait(fault);repeat(8)@(negedge n);
  if(pv||ev||retired||retire_done||wr)$fatal(1,"completion after lifetime fault");
  $display("PASS LIFETIME374 case=%0d",CASE);$finish;
 end endtask
 initial begin
  repeat(5)@(negedge h);reset=0;repeat(20)@(negedge h);
  batch374(0);
  if(CASE==1)begin wait(dut.state==dut.CAPTURE);stop=1;repeat(20)@(negedge n);if(pv||ev||wr||retired)$fatal(1,"STOP read");$display("PASS LIFETIME374 case=1");$finish;end
  wait(pv);if(kind!=0||slot!=1||tag!=64||mask!=255||rows!=48'hff6b646d2240||am!=0||tags!=0)$fatal(1,"first record");
  if(CASE==2)begin @(negedge n);pr=1;@(negedge n);pr=0;stop=1;repeat(20)@(negedge n);if(pv||ev||wr||retired)$fatal(1,"STOP RUN");$display("PASS LIFETIME374 case=2");$finish;end
  // Fill the other RAM bank while the NES first record is held.
  batch374(1);repeat(20)@(negedge h);
  if(!pv||kind!=0||slot!=1||tag!=64||mask!=255||tags!=0)$fatal(1,"pending bank changed active record");
  if(CASE==3)begin permit=1;@(negedge h);retire=1;@(negedge h);retire=0;bad374();end
  if(CASE==4)begin
   if(wr)$fatal(1,"third bank writable before mailbox credit");
   wv=1;wd=99;@(negedge h);wv=0;bad374();
  end
  consume374();end374(1);wait(pv);
  if(kind!=1||slot!=2||tag!=65||mask!=8'h35||am!=0||tags!=0)$fatal(1,"second bank record");
  if(CASE==5)begin gen=2;bad374();end
  consume374();end374(0);repeat(10)@(negedge n);
  if(!idle||fault||retired_count)$fatal(1,"full end lifetime");
  @(negedge h);retire=1;@(negedge h);retire=0;repeat(20)@(negedge n);
  if(retired_count||retire_done)$fatal(1,"retire before permit");
  permit=1;wait(retire_done);repeat(10)@(negedge n);
  if(retired_count!=1||fault)$fatal(1,"exact retire");
  gen=2;permit=0;
  batch374(2);wait(pv);
  if(kind!=0||pg!=2||slot!=3||tag!=66||mask!=255||tags!=0)$fatal(1,"bank reuse stale record");
  consume374();end374(0);permit=1;@(negedge h);retire=1;@(negedge h);retire=0;wait(retire_done);repeat(10)@(negedge n);
  if(retired_count!=2||fault)$fatal(1,"reuse final retire");
  $display("PASS LIFETIME374 case=0");$finish;
 end
 initial begin #2000000;$fatal(1,"lifetime timeout case%0d hf%0d nf%0d state%0d count%0d",CASE,dut.hf,dut.nf,dut.state,dut.count);end
endmodule
