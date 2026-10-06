// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module packet_cdc_tb;
 reg queue_clk=0,host_clk=0,q_run=1,h_run=1,reset=1;
 integer qhalf=5,hhalf=7,hphase=3,unused;
 initial begin unused=$value$plusargs("QHALF=%d",qhalf);forever begin #(qhalf);if(q_run)queue_clk=~queue_clk;end end
 initial begin unused=$value$plusargs("HHALF=%d",hhalf);unused=$value$plusargs("HPHASE=%d",hphase);#(hphase);forever begin #(hhalf);if(h_run)host_clk=~host_clk;end end
 reg [15:0] reset_epoch=1,p_epoch=1,p_seq=1;
 reg [1:0] p_op=0;reg [11:0] p_length=0;reg [7:0] p_data=0;
 wire p_accept;wire [3:0] p_error;
 reg cmd_valid=0,rsp_ready=0;wire cmd_ready;
 reg [1:0] cmd_op=0;reg [15:0] cmd_epoch=1,cmd_seq=1;reg [11:0] cmd_address=0;
 wire rsp_valid,rsp_accept,rsp_data_valid,host_read_owned;
 wire [3:0] rsp_error;wire [7:0] rsp_data;wire [11:0] rsp_length;wire [15:0] rsp_epoch,rsp_seq;
 nes_packet_cdc dut(.*);
 reg [7:0] split[0:2327],sprite[0:2051],resident[0:2007];
 integer log,checks=0,responses=0,readbytes=0;
 string trace_name;
 time request_time;reg [1:0] request_op;
 always @(posedge host_clk) if(!reset) begin
  if(cmd_valid && cmd_ready) begin
   request_time=$time;request_op=cmd_op;
   $fdisplay(log,"R %0d %0d %0d %0d %0d",$time,cmd_op,cmd_epoch,cmd_seq,cmd_address);
  end
  if(rsp_valid && rsp_ready) begin
   responses=responses+1;if(rsp_data_valid)readbytes=readbytes+1;
   $fdisplay(log,"H %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",
      $time,request_op,rsp_epoch,rsp_seq,rsp_accept,rsp_error,rsp_data_valid,rsp_data,rsp_length,host_read_owned,$time-request_time);
  end
 end
 reg [1:0] q_saved_op;
 always @(posedge queue_clk) begin
  q_saved_op=dut.q_op;
  if(!reset && q_saved_op!=0) begin
   #1;$fdisplay(log,"Q %0d %0d %0d %0d %0d %0d %0d %0d %0d",$time,q_saved_op,
     dut.q_req_epoch,dut.q_req_seq,dut.q_address,dut.q_accept,dut.q_error,dut.q_data_valid,dut.q_data);
  end
 end
 always @(posedge reset) if(log) $fdisplay(log,"X %0d %0d",$time,reset_epoch);
 function automatic [7:0] expected(input integer fixture,input integer address);
  case(fixture)
   0:expected=split[address];1:expected=sprite[address];2:expected=resident[address];
   default:expected=(address*17+fixture*29)&255;
  endcase
 endfunction
 task automatic producer(input [1:0] op,input integer len,input [7:0] data,input integer accept,input integer err);
  @(negedge queue_clk);p_op=op;p_length=len;p_data=data;
  @(posedge queue_clk);#1;
  if(p_accept!==accept[0] || p_error!==err[3:0]) $fatal(1,"producer mismatch op%0d error%0d",op,p_error);
  @(negedge queue_clk);p_op=0;
 endtask
 task automatic fill(input integer fixture,input integer size);
  producer(1,size,0,1,0);
  for(integer i=0;i<size;i=i+1)producer(2,0,expected(fixture,i),1,0);
  producer(3,0,0,1,0);
 endtask
 task automatic issue(input integer op,input integer ep,input integer seq,input integer addr);
  @(negedge host_clk);while(!cmd_ready)@(negedge host_clk);
  cmd_op=op;cmd_epoch=ep;cmd_seq=seq;cmd_address=addr;cmd_valid=1;
  @(negedge host_clk);cmd_valid=0;
  // Deliberately change external command pins while the held request is outstanding.
  cmd_op=3;cmd_epoch=65535;cmd_seq=65535;cmd_address=4095;
 endtask
 task automatic receive(input integer op,input integer ep,input integer seq,input integer accept,input integer err,input integer value,input integer len,input integer holdcycles);
  reg [58:0] held;
  while(!rsp_valid)@(negedge host_clk);
  if(rsp_accept!==accept[0] || rsp_error!==err[3:0] || rsp_epoch!==ep[15:0] || rsp_seq!==seq[15:0])
    $fatal(1,"response op%0d ep%0d seq%0d got%0d/%0d tag%0d/%0d",op,ep,seq,rsp_accept,rsp_error,rsp_epoch,rsp_seq);
  if(op==2 && accept)begin
   if(!rsp_data_valid || rsp_data!==value[7:0] || !host_read_owned)$fatal(1,"payload mismatch");
  end else if(rsp_data_valid)$fatal(1,"unexpected byte");
  if(op==1 && accept && (rsp_length!=len || !host_read_owned))$fatal(1,"acquire metadata");
  if(op==3 && accept && host_read_owned)$fatal(1,"commit ownership");
  held={rsp_accept,rsp_error,rsp_data_valid,rsp_data,rsp_length,rsp_epoch,rsp_seq,host_read_owned};
  for(integer j=0;j<holdcycles;j=j+1)begin
   cmd_valid=1;@(negedge host_clk);
   if(cmd_ready || !rsp_valid || held!=={rsp_accept,rsp_error,rsp_data_valid,rsp_data,rsp_length,rsp_epoch,rsp_seq,host_read_owned})$fatal(1,"backpressure stability");
  end
  cmd_valid=0;rsp_ready=1;@(negedge host_clk);rsp_ready=0;
 endtask
 task automatic host(input integer op,input integer ep,input integer seq,input integer addr,input integer accept,input integer err,input integer value,input integer len,input integer holdcycles);
  issue(op,ep,seq,addr);receive(op,ep,seq,accept,err,value,len,holdcycles);
 endtask
 task automatic drain(input integer fixture,input integer size,input integer ep,input integer seq);
  host(1,ep,seq,0,1,0,0,size,0);
  for(integer i=0;i<size;i=i+1)host(2,ep,seq,i,1,0,expected(fixture,i),0,0);
 endtask
 task automatic restart(input integer generation);
  reset_epoch=generation;reset=1;cmd_valid=0;rsp_ready=0;p_op=0;
  #1;if(rsp_valid || host_read_owned || cmd_ready)$fatal(1,"async reset exposure");
  #(8*(qhalf+hhalf));reset=0;
  @(negedge host_clk);while(!cmd_ready)@(negedge host_clk);
  p_epoch=generation;p_seq=1;
  repeat(6)begin @(negedge host_clk);if(rsp_valid || host_read_owned)$fatal(1,"stale response");end
 endtask
 task automatic passed(input string name);
  checks=checks+1;$display("PASS CASE %s",name);
 endtask
 initial begin
  unused=$value$plusargs("TRACE=%s",trace_name);log=$fopen(trace_name,"w");
  $readmemh("split.hex",split);$readmemh("sprite.hex",sprite);$readmemh("resident.hex",resident);
  restart(1);
  host(1,1,1,0,0,0,0,0,0);host(2,1,1,0,0,7,0,0,0);passed("empty_remote_wait");
  producer(1,2328,0,1,0);
  for(integer i=0;i<64;i=i+1)producer(2,0,expected(0,i),1,0);
  host(1,1,1,0,0,0,0,0,0);producer(3,0,0,0,5);
  if(host_read_owned)$fatal(1,"partial exposed");
  for(integer i=64;i<2328;i=i+1)producer(2,0,expected(0,i),1,0);
  producer(3,0,0,1,0);passed("partial_publish_wait");
  host(1,0,1,0,0,3,0,0,0);host(1,1,2,0,0,4,0,0,0);
  host(1,1,1,0,1,0,0,2328,0);passed("remote_token_guards");
  host(2,1,1,0,1,0,expected(0,0),0,6);passed("held_request_and_response_backpressure");
  host(3,1,1,0,0,5,0,0,0);host(2,1,1,3,0,8,0,0,0);passed("early_commit_and_address_guards");
  p_seq=2;
  fork
   fill(1,2052);
   begin for(integer i=1;i<2328;i=i+1)host(2,1,1,i,1,0,expected(0,i),0,0);end
  join
  p_seq=3;producer(1,2008,0,0,1);
  host(1,1,1,0,0,0,0,0,0);host(3,1,1,0,1,0,0,0,0);passed("two_slot_hold_and_concurrent_producer");
  fork fill(2,2008);drain(1,2052,1,2);join
  host(3,1,2,0,1,0,0,0,0);
  drain(2,2008,1,3);host(3,1,3,0,1,0,0,0,0);passed("three_actual_packet_payloads");
  issue(1,1,4,0);restart(2);passed("reset_request_in_flight");
  fill(4,4);host(1,2,1,0,1,0,0,4,0);
  issue(2,2,1,0);while(!rsp_valid)@(negedge host_clk);
  restart(3);host(2,2,1,0,0,3,0,0,0);passed("reset_held_response");
  @(negedge queue_clk);q_run=0;
  fork
   host(1,3,1,0,0,0,0,0,0);
   begin repeat(12)@(negedge host_clk);if(rsp_valid)$fatal(1,"response without queue clock");q_run=1;end
  join
  passed("stopped_queue_clock");
  issue(1,3,1,0);h_run=0;repeat(20)@(negedge queue_clk);
  if(rsp_valid)$fatal(1,"response without host clock");
  h_run=1;receive(1,3,1,0,0,0,0,0);passed("stopped_host_clock");
  @(negedge queue_clk);q_run=0;@(negedge host_clk);h_run=0;
  reset_epoch=4;reset=1;#1;
  if(rsp_valid || host_read_owned || cmd_ready)$fatal(1,"stopped reset exposure");
  #80;reset=0;h_run=1;
  repeat(10)begin @(negedge host_clk);if(cmd_ready || rsp_valid)$fatal(1,"peer not released");end
  q_run=1;while(!cmd_ready)@(negedge host_clk);
  p_epoch=4;p_seq=1;passed("common_reset_with_stopped_clocks");
  host(1,3,1,0,0,3,0,0,0);
  fill(7,17);drain(7,17,4,1);host(3,4,1,0,1,0,0,0,0);passed("fresh_generation_recovery");
  $display("PASS NES PACKET CDC checks=%0d responses=%0d readbytes=%0d",checks,responses,readbytes);
  $fclose(log);$finish;
 end
 initial begin #10000000;$fatal(1,"timeout");end
endmodule
