// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module host_stage_tb;
 reg queue_clk=0,host_clk=0,q_run=1,reset=1;
 integer qhalf=5,hhalf=7,hphase=3,unused;
 initial begin unused=$value$plusargs("QHALF=%d",qhalf);forever begin #(qhalf);if(q_run)queue_clk=~queue_clk;end end
 initial begin unused=$value$plusargs("HHALF=%d",hhalf);unused=$value$plusargs("HPHASE=%d",hphase);#(hphase);forever #(hhalf)host_clk=~host_clk;end
 reg [15:0] reset_epoch=1,p_epoch=1,p_seq=1;
 reg [1:0] p_op=0;reg [11:0] p_length=0;reg [7:0] p_data=0;
 wire p_accept;wire [3:0] p_error;
 wire cmd_valid,cmd_ready,rsp_valid,rsp_ready,rsp_accept,rsp_data_valid,host_read_owned;
 wire [1:0] cmd_op;wire [15:0] cmd_epoch,cmd_seq,rsp_epoch,rsp_seq;
 wire [11:0] cmd_address,rsp_length;wire [3:0] rsp_error;wire [7:0] rsp_data;
 reg reg_write=0,reg_read=0,data_read=0;reg [3:0] reg_address=0;reg [7:0] reg_wdata=0;
 wire [7:0] reg_rdata,data;wire reg_rvalid,data_valid,ready,busy,fault;wire [3:0] bus_error;
 nes_packet_cdc bridge(.*);
 nes_host_stage dut(.*);
 reg [7:0] split[0:2327],sprite[0:2051],resident[0:2007];
 integer log,checks=0,bytes_read=0;string trace_name;time started;
 function automatic [7:0] expected(input integer f,input integer i);
  case(f)0:expected=split[i];1:expected=sprite[i];2:expected=resident[i];default:expected=(i*17+f*29)&255;endcase
 endfunction
 task automatic passed(input string s);checks++;$display("PASS CASE %s",s);endtask
 task automatic wr(input integer a,input integer v);
  @(negedge host_clk);reg_address=a;reg_wdata=v;reg_write=1;
  @(negedge host_clk);reg_write=0;
 endtask
 task automatic rd(input integer a,input integer v);
  @(negedge host_clk);reg_address=a;reg_read=1;
  @(posedge host_clk);#1;if(!reg_rvalid || reg_rdata!==v[7:0])$fatal(1,"register %0d got %0d expected %0d",a,reg_rdata,v);
  @(negedge host_clk);reg_read=0;
 endtask
 task automatic produce(input integer op,input integer len,input integer value);
  @(negedge queue_clk);p_op=op;p_length=len;p_data=value;
  @(posedge queue_clk);#1;if(!p_accept || p_error)$fatal(1,"producer");
  @(negedge queue_clk);p_op=0;
 endtask
 task automatic fill(input integer f,input integer n);
  produce(1,n,0);for(integer i=0;i<n;i++)produce(2,0,expected(f,i));produce(3,0,0);
 endtask
 task automatic start(input integer seq);
  wr(2,reset_epoch&255);wr(3,reset_epoch>>8);wr(4,seq&255);wr(5,seq>>8);
  started=$time;wr(0,1);
 endtask
 task automatic await_ready(input integer n);
  while(!ready && !fault)@(negedge host_clk);
  if(fault || !host_read_owned)$fatal(1,"ready ownership");
  rd(0,1);rd(6,n&255);rd(7,n>>8);
 endtask
 task automatic drain(input integer f,input integer n);
  $fdisplay(log,"P %0d %0d %0d",f,n,$time-started);
  // Consecutive host edges, then arbitrary pauses, with stable registered outputs.
  for(integer i=0;i<n;i++)begin
   @(negedge host_clk);data_read=1;
   @(posedge host_clk);#1;
   if(!data_valid || data!==expected(f,i))$fatal(1,"read %0d/%0d got %0d",f,i,data);
   bytes_read++;$fdisplay(log,"B %0d %0d %0d",f,i,data);
   if(i%97==5)begin
    @(negedge host_clk);data_read=0;
    repeat(3)begin @(posedge host_clk);#1;if(data_valid)$fatal(1,"duplicate output");end
   end
  end
  @(negedge host_clk);data_read=0;
  rd(8,n&255);rd(9,n>>8);
  $fdisplay(log,"E %0d",f);
 endtask
 task automatic finish;
  wr(0,2);while(busy)@(negedge host_clk);
  if(ready || fault || host_read_owned)$fatal(1,"commit");
 endtask
 task automatic restart(input integer ep);
  reset=1;reset_epoch=ep;reg_write=0;reg_read=0;data_read=0;p_op=0;q_run=1;
  #1;if(ready || data_valid || busy || fault)$fatal(1,"reset outputs");
  repeat(10)@(negedge host_clk);reset=0;
  repeat(12)@(negedge host_clk);p_epoch=ep;p_seq=1;
 endtask
 initial begin
  unused=$value$plusargs("TRACE=%s",trace_name);log=$fopen(trace_name,"w");
  $readmemh("split.hex",split);$readmemh("sprite.hex",sprite);$readmemh("resident.hex",resident);
  restart(1);
  start(1);while(busy)@(negedge host_clk);rd(0,0);passed("empty_retry");
  produce(1,2328,0);for(integer i=0;i<30;i++)produce(2,0,expected(0,i));
  start(1);while(busy)@(negedge host_clk);
  if(ready)$fatal(1,"partial exposure");passed("partial_publish_hidden");
  for(integer i=30;i<2328;i++)produce(2,0,expected(0,i));produce(3,0,0);
  start(1);
  @(negedge host_clk);data_read=1;@(posedge host_clk);#1;if(data_valid)$fatal(1,"early data");
  @(negedge host_clk);data_read=0;
  wr(4,99);if(bus_error!=1)$fatal(1,"busy config");wr(1,0);
  await_ready(2328);
  wr(0,2);if(bus_error!=5 || !ready || !host_read_owned)$fatal(1,"early release");wr(1,0);
  passed("prefetch_ready_and_early_commit");
  drain(0,2328);
  @(negedge host_clk);data_read=1;@(posedge host_clk);#1;if(data_valid || bus_error!=6)$fatal(1,"overread");
  @(negedge host_clk);data_read=0;wr(1,0);finish();passed("split_registered_burst");
  p_seq=2;fill(1,2052);start(2);await_ready(2052);drain(1,2052);finish();
  p_seq=3;fill(2,2008);start(3);await_ready(2008);drain(2,2008);finish();passed("sprite_resident_payloads");
  p_seq=4;fill(3,3072);start(4);await_ready(3072);
  @(negedge queue_clk);q_run=0;drain(3,3072);wr(0,2);
  repeat(30)@(negedge host_clk);if(!busy || ready || !host_read_owned)$fatal(1,"stopped commit");
  q_run=1;while(busy)@(negedge host_clk);if(host_read_owned)$fatal(1,"resume commit");
  passed("max_packet_stopped_queue_drain");
  p_seq=5;fill(4,17);start(6);while(busy)@(negedge host_clk);
  if(!fault || ready || bus_error!=4)$fatal(1,"sequence fault");passed("bad_token_latched");
  restart(2);fill(4,17);start(1);while(dut.filled<4)@(negedge host_clk);
  restart(3);if(ready || data_valid)$fatal(1,"stale fill");passed("reset_during_prefetch");
  fill(4,17);start(1);await_ready(17);restart(4);
  @(negedge host_clk);data_read=1;@(posedge host_clk);#1;if(data_valid)$fatal(1,"stale ready");
  @(negedge host_clk);data_read=0;passed("reset_ready_hides_ram");
  fill(4,17);start(1);await_ready(17);wr(1,0);drain(4,17);finish();passed("new_generation_recovery");
  $display("PASS NES HOST STAGE checks=%0d readbytes=%0d",checks,bytes_read);$fclose(log);$finish;
 end
 initial begin #30000000;$fatal(1,"watchdog");end
endmodule
