// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module packet_queue_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1;reg [15:0] reset_epoch=1;
 reg [1:0] p_op=0,c_op=0;
 reg [15:0] p_epoch=1,p_seq=1,c_epoch=1,c_seq=1;
 reg [11:0] p_length=0,c_address=0;reg [7:0] p_data=0;
 wire p_accept,c_accept,c_data_valid,packet_ready,consumer_active;
 wire [3:0] p_error,c_error,slot_states;
 wire [7:0] c_data;wire [11:0] ready_length;wire [15:0] ready_sequence,epoch;
 nes_packet_queue dut(.*);
 reg [7:0] split[0:2327],sprite[0:2051],resident[0:2007];
 integer log,cycles=0,writes=0,reads=0,checks=0;
 always @(posedge clk) begin
  #2;cycles=cycles+1;
  if(p_accept && p_op==2) writes=writes+1;
  if(c_data_valid) reads=reads+1;
  if(p_op!=0 || c_op!=0 || reset)
   $fdisplay(log,"%0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",
     cycles,reset,p_op,p_accept,p_error,c_op,c_accept,c_error,c_data_valid,c_data,slot_states,packet_ready,consumer_active,epoch);
  if(c_data_valid && !consumer_active) $fatal(1,"read without ownership");
 end
 function automatic [7:0] expected(input integer fixture,input integer address);
  case(fixture)
   0:expected=split[address];
   1:expected=sprite[address];
   2:expected=resident[address];
   default:expected=(address*17+fixture*29)&255;
  endcase
 endfunction
 task automatic producer(input [1:0] op,input integer len,input [7:0] data,input integer accept,input integer err);
  @(negedge clk);p_op=op;p_length=len;p_data=data;
  @(posedge clk);#1;
  if(p_accept!==accept[0] || p_error!==err[3:0]) $fatal(1,"producer op%0d seq%0d got%0d/%0d expected%0d/%0d",op,p_seq,p_accept,p_error,accept,err);
  @(negedge clk);p_op=0;
 endtask
 task automatic consumer(input [1:0] op,input integer address,input integer accept,input integer err,input integer value);
  @(negedge clk);c_op=op;c_address=address;
  @(posedge clk);#1;
  if(c_accept!==accept[0] || c_error!==err[3:0]) $fatal(1,"consumer op%0d seq%0d got%0d/%0d expected%0d/%0d",op,c_seq,c_accept,c_error,accept,err);
  if(op==2 && accept) begin
   if(c_data_valid!==1 || c_data!==value[7:0]) $fatal(1,"payload mismatch address%0d",address);
  end else if(c_data_valid!==0) $fatal(1,"unexpected read valid");
  @(negedge clk);c_op=0;
 endtask
 task automatic fill(input integer fixture,input integer size);
  producer(1,size,0,1,0);
  for(integer i=0;i<size;i=i+1) producer(2,0,expected(fixture,i),1,0);
  producer(3,0,0,1,0);
 endtask
 task automatic drain(input integer fixture,input integer size);
  consumer(1,0,1,0,0);
  for(integer i=0;i<size;i=i+1) consumer(2,i,1,0,expected(fixture,i));
 endtask
 task automatic restart(input integer generation);
  @(negedge clk);reset=1;reset_epoch=generation;p_op=0;c_op=0;
  repeat(2) @(negedge clk);reset=0;@(negedge clk);
  if(slot_states!==0 || packet_ready || consumer_active || epoch!==generation[15:0]) $fatal(1,"reset state");
 endtask
 task automatic passed(input string name);
  checks=checks+1;$display("PASS CASE %s",name);
 endtask
 initial begin
  log=$fopen("ownership.tsv","w");
  $readmemh("split.hex",split);$readmemh("sprite.hex",sprite);$readmemh("resident.hex",resident);
  restart(1);
  consumer(1,0,0,0,0);consumer(2,0,0,7,0);passed("empty_wait");
  producer(1,0,0,0,2);producer(1,3073,0,0,2);passed("length_bounds");
  p_epoch=0;producer(1,2328,0,0,3);p_epoch=1;
  p_seq=2;producer(1,2328,0,0,4);p_seq=1;passed("producer_tokens");
  producer(1,2328,0,1,0);
  for(integer i=0;i<64;i=i+1) producer(2,0,expected(0,i),1,0);
  producer(3,0,0,0,5);consumer(1,0,0,0,0);consumer(2,0,0,7,0);
  if(packet_ready || consumer_active) $fatal(1,"partial packet exposed");
  for(integer i=64;i<2328;i=i+1) producer(2,0,expected(0,i),1,0);
  producer(3,0,0,1,0);
  if(!packet_ready || ready_length!=2328 || ready_sequence!=1) $fatal(1,"metadata");
  passed("partial_publish_gate");
  p_seq=2;fill(1,2052);p_seq=3;producer(1,2008,0,0,1);passed("two_full_slots");
  c_epoch=0;consumer(1,0,0,3,0);c_epoch=1;
  c_seq=2;consumer(1,0,0,4,0);c_seq=1;
  consumer(1,0,1,0,0);consumer(3,0,0,5,0);consumer(2,1,0,8,0);
  producer(1,2008,0,0,1);passed("consumer_tokens_and_early_commit");
  for(integer i=0;i<2328;i=i+1) consumer(2,i,1,0,expected(0,i));
  consumer(2,2328,0,8,0);producer(1,2008,0,0,1);
  c_epoch=0;consumer(3,0,0,3,0);c_epoch=1;consumer(3,0,1,0,0);
  passed("split_integrity_and_commit_ownership");
  c_seq=2;
  fork fill(2,2008);drain(1,2052);join
  consumer(3,0,1,0,0);passed("simultaneous_independent_slots");
  c_seq=3;drain(2,2008);consumer(3,0,1,0,0);passed("resident_integrity");
  p_seq=4;producer(1,16,0,1,0);producer(2,0,55,1,0);
  restart(2);producer(3,0,0,0,3);consumer(3,0,0,3,0);
  p_epoch=2;c_epoch=2;p_seq=1;c_seq=1;consumer(1,0,0,0,0);passed("reset_writing_stale_tokens");
  fill(3,16);restart(3);consumer(1,0,0,3,0);
  p_epoch=3;c_epoch=3;p_seq=1;c_seq=1;consumer(1,0,0,0,0);passed("reset_ready");
  fill(4,16);consumer(1,0,1,0,0);consumer(2,0,1,0,expected(4,0));
  restart(4);consumer(2,1,0,3,0);consumer(3,0,0,3,0);
  p_epoch=4;c_epoch=4;p_seq=1;c_seq=1;consumer(1,0,0,0,0);passed("reset_reading");
  producer(1,3072,0,1,0);
  for(integer i=0;i<3072;i=i+1) producer(2,0,expected(5,i),1,0);
  producer(2,0,255,0,6);producer(3,0,0,1,0);
  drain(5,3072);consumer(3,0,1,0,0);passed("full_capacity_no_overwrite");
  for(integer n=2;n<66;n=n+1) begin
   p_seq=n;c_seq=n;fill(n,(n%31)+1);drain(n,(n%31)+1);consumer(3,0,1,0,0);
  end
  passed("ring_reuse_64_packets");
  $display("PASS NES PACKET QUEUE checks=%0d writes=%0d reads=%0d cycles=%0d",checks,writes,reads,cycles);
  $fclose(log);$finish;
 end
 initial begin #5000000;$fatal(1,"timeout");end
endmodule
