// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module tb_nes_window957;
 tb_nes_port914 #(.WINDOW957(1),.G(16'd1410)) b();
 integer edges[$], cursor, tick, gap, lead, start_tick, last_slot;
 bit full_obj;
 integer grants=0, foreground=0, hints=0, first=-1, last=-1, longest=0;
 integer requested=-1, prev_addr=-1, prev_owner=-1, last_response=-1;
 bit live=0;
 wire request=b.source.shared_req;
 wire grant=request && b.source.shared_ready;
 wire [21:0] address=b.source.shared_address;
 wire [1:0] owner=b.source.ahead.foreground?0:b.source.ahead.spec?1:2;
 always @(negedge b.clk) if(live)begin
  tick++;
  while(cursor<edges.size() && edges[cursor]<tick)cursor++;
  b.qualified=(cursor<edges.size() && edges[cursor]==tick);
 end
 always @(posedge b.clk) if(live && b.done_count==0)begin
  if(!request) requested=-1;
  else if(requested<0 || prev_addr!=address || prev_owner!=owner) requested=tick;
  prev_addr=address;prev_owner=owner;
  if(grant)begin
   if(!b.qualified || requested<0 || b.core_req)$fatal(1,"illegal grant");
   if(first<0)first=tick;
   $display("FILL957 owner=%0d addr=%0d request=%0d grant=%0d prev_response=%0d",owner,address,requested,tick,last_response);
   if(tick-requested>longest)longest=tick-requested;
   last=tick;grants++;if(owner==0)foreground++;else hints++;
   requested=-1;
  end
  if(b.mresp)last_response=tick;
 end
 string calendar;
 integer fd, value, splits=0;
 initial begin
  if(!$value$plusargs("calendar=%s",calendar)||!$value$plusargs("gap=%d",gap)||
     !$value$plusargs("lead=%d",lead))$fatal;
  fd=$fopen(calendar,"r");if(!fd)$fatal;
  while($fscanf(fd,"%d",value)==1)begin
   if(edges.size() && value-edges[$]>200000)begin
    splits++;if(splits==gap)last_slot=edges[$];
   end
   edges.push_back(value);
  end
  $fclose(fd);
  if(last_slot==0 || splits<gap)$fatal;
  full_obj=$test$plusargs("full_obj");
  b.reverse_rows957=full_obj;
  #2;b.reset=1;repeat(10)@(negedge b.clk);b.reset=0;
  wait(b.cap_ready);@(negedge b.clk);b.cap_start=1;@(negedge b.clk);b.cap_start=0;
  // Seven high-plane bytes reside in the capture. The full OBJ descriptor
  // must fetch the other nine bytes and still produce the same 32-byte tile.
  if(full_obj)for(int row=0;row<7;row++)begin
   while(!b.cap_sample_ready)@(negedge b.clk);
   b.cap_addr={13'h118,1'b1,row[2:0]};b.cap_data=b.content(13'h118,row,1'b1);
   b.cap_sample=1;@(negedge b.clk);b.cap_sample=0;
   repeat(3)@(negedge b.clk);
  end
  repeat(8)@(negedge b.clk);b.cap_seal=1;@(negedge b.clk);b.cap_seal=0;
  repeat(280)@(negedge b.clk);
  @(posedge b.clk);#1;tick=last_slot-lead;start_tick=tick;cursor=0;b.qualified=0;live=1;
  b.count=1;b.size=0;b.crc='1;
  if(full_obj)begin b.send_byte(1);b.send_byte(0);end else b.send_byte(8'h81);
  b.send_byte(b.G[7:0]);b.send_byte(b.G[15:8]);b.send_byte(8);
  b.send_byte(0);b.send_byte(8'h18);b.send_byte(1);b.send_byte(255);
  if(full_obj)begin
   // The ARM encoder keeps nonidentity row maps in the full 16-byte form.
   for(int j=0;j<6;j++) b.send_byte((~48'hff6b646d2240)>>(8*j));
   b.send_byte(1);
  end
  @(negedge b.host);b.write_en=0;b.seal=1;@(negedge b.host);b.seal=0;
  wait(b.done_count==1);@(negedge b.host);
  if(b.bytes_out!=32 || grants!=(full_obj?9:8) || b.trace_run.bulk_fault || b.trace_run.consume_fault)$fatal(1,"incomplete first tile, grants=%0d",grants);
  if(lead==75 && !(first==last_slot && last>last_slot && longest>320000))$fatal(1,"no cross-window read");
  if(lead>=1100 && last>last_slot)$fatal(1,"missed early deadline");
  if(lead<0 && !(first>last_slot && longest>320000))$fatal(1,"no first-grant wait");
  $display("RESULT957 gap=%0d full=%0d lead=%0d end_slot=%0d plan_start=%0d first=%0d last=%0d done=%0d grants=%0d demand=%0d prefetch=%0d max_wait=%0d",gap,full_obj,lead,last_slot,start_tick,first,last,tick,grants,foreground,hints,longest);
  $display("PASS957 bytes=%0d",b.bytes_out);$finish;
 end
endmodule
