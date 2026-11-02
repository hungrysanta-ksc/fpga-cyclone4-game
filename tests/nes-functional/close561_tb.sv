// SPDX-License-Identifier: MIT
`timescale 1ps/1ps
module close561_tb;
 reg nc=0,hc=0,reset=1,stop=0,pv=0,allow=1,ending=0;
 always #23281 nc=!nc;
 initial begin if($test$plusargs("SHIFT"))#3100;forever #5952 hc=!hc;end
 reg [1:0] kind;reg [9:0] slot;reg [12:0] tag;reg [15:0] gen=952;
 wire permit,ready,tv,tr,done,req,tf,bf,er,sealed_end;
 wire [16:0] addr;reg [16:0] reply_addr;reg reply=0;reg [7:0] romdata;
 always @(posedge nc)begin
   reply<=req&&allow;
   if(req&&allow)begin reply_addr<=addr;romdata<=addr[11:4];end
 end
 wire [7:0] pixel;wire [4:0] idx;wire [5:0] bytes_n;wire [1:0] tk;
 wire [9:0] ts;wire [15:0] tg;
 nes_tile205 #(.EXTERNAL_PLAN(1)) tile(.clk(nc),.reset(reset),.stop(stop),.lease_valid(1'b1),.lease_generation(gen),
  .plan_valid(pv&&permit),.plan_ready(ready),.plan_kind(kind),.plan_generation(gen),.plan_slot(slot),.plan_tag(tag),
  .plan_rows(48'd0),.plan_mask(8'hff),.plan_alt_mask(8'd0),.plan_alt_tags(104'd0),.mem_idle(1'b1),.mem_ready(allow),
  .mem_request(req),.mem_address(addr),.mem_response(reply),.mem_error(1'b0),.response_address(reply_addr),
  .response_generation(gen),.response_data(romdata),.out_valid(tv),.out_ready(tr),.out_data(pixel),.out_index(idx),
  .out_length(bytes_n),.out_kind(tk),.out_slot(ts),.out_generation(tg),.fault(tf),.done(done));
 wire avail,ck,consume,bad_token,cmd_error,oe;
 wire [11:0] length;wire [31:0] token,taken;wire [9:0] dest;wire [15:0] generation;
 reg [23:0] bus=0;reg rd=1,wr=1;reg [7:0] wdata=0;wire [7:0] rdata;
 nes_tile_bulk206 bulk(.nes_clk(nc),.host_clk(hc),.active(1'b1),.reset(reset),.stop(stop),.source_fault(tf),
`ifdef EARLY
  .plan_valid(pv),.plan_taken(pv&&permit&&ready),.plan_kind(kind),.plan_slot(slot),.plan_generation(gen),.plan_permit(permit),
`endif
  .tile_valid(tv),.tile_ready(tr),.tile_data(pixel),.tile_index(idx),.tile_length(bytes_n),.tile_kind(tk),
  .tile_slot(ts),.tile_generation(tg),.end_valid(ending),.end_ready(er),.end_generation(gen),.token_seed(32'd1),
  .chunk_ready(avail),.chunk_kind(ck),.chunk_length(length),.chunk_token(token),.chunk_slot(dest),.chunk_generation(generation),
  .consume(consume),.consume_token(taken),.consume_error(bad_token),.address(bus),.read_n(rd),.write_n(wr),.data_out(rdata),
  .oe_n(oe),.fault(bf),.end_sealed(sealed_end));
`ifndef EARLY
 assign permit=1;
`endif
 nes_bulk_control194 ctl(.clk(hc),.active(1'b1),.reset(reset),.stop(stop),.fault(bf),
  .chunk_ready(avail),.chunk_kind(ck),.chunk_length(length),.chunk_token(token),.chunk_slot(dest),.chunk_generation(generation),
  .address(bus),.read_n(rd),.write_n(wr),.data_in(wdata),.consume(consume),.consume_token(taken),.command_error(cmd_error));
 reg saw_end=0,wrong=0;
 always @(posedge hc)begin
   if(sealed_end)saw_end<=1;
   if(cmd_error)wrong<=1;
   if(tf||bf||bad_token)$fatal(1,"unexpected source or aperture fault");
 end
 task plan(input [1:0] k,input [9:0] s,input [12:0] t);
  @(negedge nc);kind=k;slot=s;tag=t;pv=1;
  do @(posedge nc);while(!(permit&&ready));
  @(negedge nc);pv=0;
 endtask
 task write_reg(input [23:0] a,input [7:0] b);
  @(negedge hc);bus=a;wdata=b;wr=0;repeat(6)@(negedge hc);wr=1;repeat(6)@(negedge hc);
 endtask
 task ack(input [31:0] t);
  for(int i=0;i<4;i++)write_reg(24'h604c+i,t>>(8*i));
  write_reg(24'h6050,8'ha5);
 endtask
 task chunk(input integer n,input integer section,input integer offset,input integer id);
  wait(avail);if(length!=n||ck!=section||dest!=offset||token!=id||generation!=gen)$fatal(1,"descriptor");
  for(int i=0;i<n;i++)begin
   @(negedge hc);bus=24'h400800+i;rd=0;repeat(5)@(negedge hc);
   if(oe||rdata!==(section?(i<16?8'd9:8'd0):8'(1+i/16)))$fatal(1,"payload");
  end
  $display("TRACE READ_LAST %0d %0t",id,$time);rd=1;
  if(id==1)begin ack(77);if(!wrong||!avail||token!=1)$fatal(1,"stale token freed bank");end
  ack(id);$display("TRACE RETURN %0d %0t",id,$time);
 endtask
 always @(posedge avail)$display("TRACE PUBLISH %0t",$time);
 always @(posedge hc)if(consume)$display("TRACE BANK_FREE %0d %0t",taken,$time);
 always @(posedge nc)if(pv&&kind==1&&permit&&ready)$display("TRACE PLAN_TAKEN %0t",$time);
`ifdef EARLY
 always @(posedge nc)if(bulk.announce&&!bulk.sending&&bulk.box_ready)$display("TRACE MARKER_SENT %0t",$time);
`endif
 initial begin
  #120000;reset=0;repeat(20)@(negedge nc);
  for(int i=0;i<3;i++)begin plan(0,119+i,1+i);wait(done);end
  $display("TRACE BG_DONE %0t",$time);allow=0;
  if($test$plusargs("CANCEL"))begin
   @(negedge nc);kind=1;slot=27;tag=9;pv=1;
`ifdef EARLY
   wait(bulk.announced);@(negedge nc);
`endif
   stop=1;pv=0;repeat(5)@(negedge nc);stop=0;repeat(25)@(negedge nc);
   if(avail||saw_end||consume||!er)$fatal(1,"STOP drain");
   $display("PASS561 STOP");$finish;
  end
  plan(1,27,9);wait(req);repeat(25)@(negedge nc);
`ifdef EARLY
  if($test$plusargs("PARTIAL"))begin
   wait(avail);bus=24'h400800;rd=0;repeat(6)@(negedge hc);
   if(oe||rdata!=1)$fatal(1,"partial read");
   stop=1;repeat(5)@(negedge nc);if(!oe||avail||saw_end)$fatal(1,"STOP leaked open bank");
   rd=1;stop=0;gen=953;allow=1;repeat(25)@(negedge nc);
   plan(0,119,1);wait(done);@(negedge nc);ending=1;do @(posedge nc);while(!er);@(negedge nc);ending=0;
   chunk(16,0,119,1);if(!saw_end)$fatal(1,"restart END");
   $display("PASS561 PARTIAL");$finish;
  end
`endif
`ifdef EARLY
  if(!avail||saw_end)$fatal(1,"boundary missed");chunk(48,0,119,1);
`else
  if(avail||saw_end)$fatal(1,"unexpected early close");
`endif
  $display("TRACE OBJ_ROM_GRANT %0t",$time);allow=1;wait(done);
`ifndef EARLY
  chunk(48,0,119,1);
`endif
  allow=0;plan(1,31,9);wait(req);repeat(25)@(negedge nc);
`ifdef EARLY
  if(!avail||saw_end)$fatal(1,"sparse boundary missed");chunk(32,1,27,2);
`else
  if(avail||saw_end)$fatal(1,"sparse chunk closed too soon");
`endif
  allow=1;wait(done);
  @(negedge nc);ending=1;do @(posedge nc);while(!er);@(negedge nc);ending=0;
`ifndef EARLY
  chunk(32,1,27,2);
`endif
  chunk(32,1,31,3);repeat(20)@(negedge nc);
  if(!saw_end||avail)$fatal(1,"END or credit");
  $display("PASS561 NORMAL");$finish;
 end
 initial begin #1000000000;$fatal(1,"timeout");end
endmodule
