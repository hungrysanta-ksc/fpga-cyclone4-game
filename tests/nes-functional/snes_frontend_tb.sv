// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module snes_frontend_tb;
 reg queue_clk=0,host_clk=0,reset=1;
 real qhalf=23.280423,hhalf=5.952381,hphase=1.1;
 integer unused;
 initial begin unused=$value$plusargs("QHALF=%f",qhalf);forever #(qhalf)queue_clk=~queue_clk;end
 initial begin unused=$value$plusargs("HHALF=%f",hhalf);unused=$value$plusargs("HPHASE=%f",hphase);#(hphase);forever #(hhalf)host_clk=~host_clk;end
 reg [15:0] reset_epoch=1,p_epoch=1,p_seq=1;reg [1:0] p_op=0;
 reg [11:0] p_length=0;reg [7:0] p_data=0;wire p_accept;wire [3:0] p_error;
 wire cmd_valid,cmd_ready,rsp_valid,rsp_ready,rsp_accept,rsp_data_valid,host_read_owned;
 wire [1:0] cmd_op;wire [15:0] cmd_epoch,cmd_seq,rsp_epoch,rsp_seq;
 wire [11:0] cmd_address,rsp_length;wire [3:0] rsp_error;wire [7:0] rsp_data;
 wire reg_write,reg_read,data_read;wire [3:0] reg_address;wire [7:0] reg_wdata,reg_rdata,data;
 wire reg_rvalid,data_valid,ready,busy,fault;wire [3:0] bus_error,frontend_error;
 reg [23:0] snes_addr=0;reg read_n=1,write_n=1,romsel_n=1;reg [7:0] snes_data_in=0;
 wire [7:0] bus_data;wire databus_oe_n,databus_dir;
 nes_transport transport(.*);
 assign data_read=transport.data_read;assign reg_write=transport.reg_write;
 reg [7:0] split[0:2327],sprite[0:2051],resident[0:2007];
 integer log,checks=0,reads=0,data_pulses=0,write_pulses=0;string trace_name;
 real max_latency=0;
 always @(posedge host_clk)if(!reset)begin
  if(data_read)data_pulses++;
  if(reg_write)write_pulses++;
 end
 function automatic [7:0] expected(input integer f,input integer i);
  case(f)0:expected=split[i];1:expected=sprite[i];2:expected=resident[i];default:expected=(i*17+f*29)&255;endcase
 endfunction
 task automatic passed(input string s);checks++;$display("PASS CASE %s",s);endtask
 task automatic wr(input integer a,input integer v);
  snes_addr=a;snes_data_in=v;romsel_n=1;#20;write_n=0;
  #180;write_n=1;#20;snes_addr=24'h123456;snes_data_in=255;#80;
 endtask
 task automatic rd(input integer a,input integer expected_value,input integer payload,input integer hold_ns);
  integer pulses_before;real start,latency;
  pulses_before=data_pulses;snes_addr=a;romsel_n=payload?0:1;#20;read_n=0;start=$realtime;
  while(databus_oe_n && $realtime-start<120)#1;
  latency=$realtime-start;
  if(databus_oe_n || !databus_dir || bus_data!==expected_value[7:0])$fatal(1,"read %h got%h expected%h latency%f flags%h",a,bus_data,expected_value,latency,frontend_error);
  if(latency>5*(hhalf*2)+1)$fatal(1,"latency bound");
  if(latency>max_latency)max_latency=latency;
  #(hold_ns-latency);
  if(bus_data!==expected_value[7:0] || databus_oe_n)$fatal(1,"held bus changed");
  if(data_pulses!=pulses_before+payload)$fatal(1,"duplicate/missing consumption");
  if(payload)begin reads++;$fdisplay(log,"B %0d %0d %0d %0f",p_seq,a-24'h408000,bus_data,latency);end
  read_n=1;#0.001;if(!databus_oe_n || databus_dir)$fatal(1,"raw release");
  #20;snes_addr=24'habcdef;#80;
 endtask
 task automatic quiet_read(input integer a,input integer rom,input integer request_delta=0);
  integer pulses_before;pulses_before=data_pulses;
  snes_addr=a;romsel_n=rom;#20;read_n=0;
  #180;if(!databus_oe_n || databus_dir || data_pulses!=pulses_before+request_delta)$fatal(1,"unmapped drove/consumed");
  read_n=1;#100;
 endtask
 task automatic produce(input integer op,input integer n,input integer value);
  @(negedge queue_clk);p_op=op;p_length=n;p_data=value;
  @(posedge queue_clk);#1;if(!p_accept || p_error)$fatal(1,"producer");
  @(negedge queue_clk);p_op=0;
 endtask
 task automatic fill(input integer f,input integer n);
  produce(1,n,0);for(integer i=0;i<n;i++)produce(2,0,expected(f,i));produce(3,0,0);
 endtask
 task automatic start(input integer seq);
  wr(24'h006002,reset_epoch&255);wr(24'h006003,reset_epoch>>8);wr(24'h006004,seq&255);wr(24'h006005,seq>>8);wr(24'h006000,1);
  while(!ready && !fault)#20;if(fault)$fatal(1,"start fault");
 endtask
 task automatic restart(input integer ep);
  read_n=1;write_n=1;reset=1;reset_epoch=ep;p_op=0;#1;
  if(!databus_oe_n || databus_dir)$fatal(1,"reset drive");
  #400;reset=0;p_epoch=ep;p_seq=1;#400;
 endtask
 task automatic finish;
  wr(24'h006000,2);while(busy)#20;
  if(ready || fault || host_read_owned || frontend_error)$fatal(1,"commit");
 endtask
 initial begin
  unused=$value$plusargs("TRACE=%s",trace_name);log=$fopen(trace_name,"w");
  $readmemh("split.hex",split);$readmemh("sprite.hex",sprite);$readmemh("resident.hex",resident);
  restart(1);
  quiet_read(24'h00600b,1);quiet_read(24'h806000,1);quiet_read(24'h408c00,0);quiet_read(24'h408000,1);
  rd(24'h006000,0,0,180);rd(24'h00600a,0,0,180);passed("exact_decode_unmapped_idle");
  wr(24'h006002,1);rd(24'h006002,1,0,600);
  wr(24'h006002,0);rd(24'h006002,0,0,180);passed("write_end_bundle_and_held_register");
  fill(0,2328);start(1);rd(24'h006000,1,0,180);rd(24'h006006,24,0,180);rd(24'h006007,9,0,180);
  wr(24'h006000,2);rd(24'h006001,5,0,180);wr(24'h006001,0);passed("ready_length_early_commit");
  $fdisplay(log,"P 0 2328");
  for(integer i=0;i<2328;i++)rd(24'h408000+i,expected(0,i),1,i==0?600:180);
  finish();passed("split_dma_held_read_one_byte");
  p_seq=2;fill(1,2052);start(2);$fdisplay(log,"P 1 2052");
  for(integer i=0;i<2052;i++)rd(24'h408000+i,expected(1,i),1,180);
  finish();p_seq=3;fill(2,2008);start(3);$fdisplay(log,"P 2 2008");
  for(integer i=0;i<2008;i++)rd(24'h408000+i,expected(2,i),1,180);
  finish();passed("sprite_resident_incrementing_dma");
  restart(2);fill(3,8);start(1);
  quiet_read(24'h408001,0);rd(24'h00600a,2,0,180);if(transport.stage.consumed!=0)$fatal(1,"bad address consumed");
  passed("out_of_order_read_rejected");
  restart(3);fill(3,8);start(1);
  snes_addr=24'h408000;romsel_n=0;#20;read_n=0;#120;
  if(databus_oe_n)$fatal(1,"missing first payload");
  snes_addr=24'h408001;#0.001;if(!databus_oe_n)$fatal(1,"address drive leakage");
  #100;snes_addr=24'h408000;#1;if(!databus_oe_n)$fatal(1,"restored address redrove aborted data");
  read_n=1;#100;rd(24'h00600a,1,0,180);passed("held_read_address_change_blocks_drive");
  restart(4);
  snes_addr=24'h006002;snes_data_in=99;#20;read_n=0;write_n=0;#180;
  if(!databus_oe_n || databus_dir)$fatal(1,"conflict drive");
  read_n=1;write_n=1;#120;rd(24'h00600a,4,0,180);rd(24'h006002,0,0,180);passed("read_write_conflict_no_command");
  restart(5);fill(3,8);start(1);
  snes_addr=24'h408000;romsel_n=0;#20;read_n=0;#120;
  reset=1;#0.001;if(!databus_oe_n || databus_dir)$fatal(1,"async reset release");passed("reset_during_drive");
  restart(6);fill(4,17);start(1);
  snes_addr=24'h408000;romsel_n=0;#20;read_n=0;#25;read_n=1;#150;
  if(!databus_oe_n || (transport.stage.consumed!=0 && frontend_error==0))$fatal(1,"short pulse exposure");
  passed("early_release_requires_reset");
  restart(7);fill(4,17);start(1);$fdisplay(log,"P 4 17");
  for(integer i=0;i<17;i++)rd(24'h408000+i,expected(4,i),1,180);
  finish();passed("fresh_generation_after_abort");
  restart(8);fill(3,1);start(1);$fdisplay(log,"P 3 1");
  rd(24'h408000,expected(3,0),1,180);
  quiet_read(24'h408001,0,1);rd(24'h00600a,8,0,180);
  if(transport.stage.consumed!=1 || !host_read_owned)$fatal(1,"overread ownership");
  passed("overread_no_response_no_release");
  restart(9);fill(3,8);start(1);
  snes_addr=24'h408000;romsel_n=0;#20;read_n=0;#120;
  if(databus_oe_n)$fatal(1,"payload first drive");romsel_n=1;#0.001;
  if(!databus_oe_n)$fatal(1,"deselect release");#100;romsel_n=0;#1;
  if(!databus_oe_n)$fatal(1,"reselect redrove aborted data");
  read_n=1;#100;rd(24'h00600a,1,0,180);passed("romsel_abort_latched");
  $display("PASS NES SNES FRONTEND checks=%0d readbytes=%0d max_latency_ns=%0f",checks,reads,max_latency);
  $fclose(log);$finish;
 end
 initial begin #30000000;$fatal(1,"watchdog");end
endmodule
