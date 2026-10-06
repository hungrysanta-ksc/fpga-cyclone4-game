// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module h1_pattern_tb;
 reg queue_clk=0,host_clk=0,reset=1;
 real qhalf=23.280423,hhalf=5.952381,hphase=1.1;
 integer unused;
 initial begin unused=$value$plusargs("QHALF=%f",qhalf);forever #(qhalf)queue_clk=~queue_clk;end
 initial begin unused=$value$plusargs("HHALF=%f",hhalf);unused=$value$plusargs("HPHASE=%f",hphase);#(hphase);forever #(hhalf)host_clk=~host_clk;end
 reg [15:0] reset_epoch=1;
 reg [23:0] snes_addr=0;reg read_n=1,write_n=1,romsel_n=1;reg [7:0] snes_data_in=0;
 wire [7:0] bus_data;wire databus_oe_n,databus_dir,ready,busy,fault,host_read_owned,producer_fault,exhausted;
 wire [3:0] bus_error,frontend_error,producer_error;wire [15:0] published;
 nes_h1_pattern dut(.*);
 reg [7:0] golden[0:6143];integer log,checks=0,readbytes=0;string trace;
 task automatic passed(input string s);checks++;$display("PASS CASE %s",s);endtask
 task automatic wr(input integer a,input integer v);
  snes_addr=a;snes_data_in=v;romsel_n=1;#20;write_n=0;#180;write_n=1;#20;snes_addr=24'h123456;#80;
 endtask
 task automatic rd(input integer a,input integer want,input integer payload);
  real start;
  snes_addr=a;romsel_n=payload?0:1;#20;read_n=0;start=$realtime;
  while(databus_oe_n && $realtime-start<120)#1;
  if(databus_oe_n || !databus_dir || bus_data!==want[7:0])$fatal(1,"read %h got%h want%h flags%h",a,bus_data,want,frontend_error);
  #(180-($realtime-start));
  if(databus_oe_n || bus_data!==want[7:0])$fatal(1,"unstable");
  if(payload)begin readbytes++;$fdisplay(log,"%0d",bus_data);end
  read_n=1;#0.001;if(!databus_oe_n || databus_dir)$fatal(1,"release");
  #20;snes_addr=24'habcdef;#80;
 endtask
 task automatic acquire(input integer seq);
  wr(24'h006002,reset_epoch&255);wr(24'h006003,reset_epoch>>8);
  wr(24'h006004,seq&255);wr(24'h006005,seq>>8);wr(24'h006000,1);
  while(!ready && !fault)#20;
  if(fault || bus_error || frontend_error || producer_fault)$fatal(1,"acquire fault");
  rd(24'h006006,0,0);rd(24'h006007,8,0);
 endtask
 task automatic commit;
  rd(24'h006008,0,0);rd(24'h006009,8,0);wr(24'h006000,2);
  while(busy)#20;
  if(ready || fault || host_read_owned || bus_error || frontend_error || producer_fault)$fatal(1,"commit");
 endtask
 task automatic restart(input integer ep);
  reset=1;reset_epoch=ep;read_n=1;write_n=1;#1;
  if(!databus_oe_n || databus_dir)$fatal(1,"reset drive");
  #400;reset=0;#400;
 endtask
 initial begin
  unused=$value$plusargs("TRACE=%s",trace);log=$fopen(trace,"w");$readmemh("h1-pattern.hex",golden);
  restart(1);
  while(published!=2)#100;
  repeat(800)@(posedge queue_clk);
  if(published!=2 || producer_fault || exhausted || dut.producer.p_seq!=3)$fatal(1,"full queue lost sequence");
  passed("two_slots_backpressure_holds_sequence");
  for(integer seq=1;seq<=6;seq++)begin
   acquire(seq);
   for(integer i=0;i<2048;i++)rd(24'h408000+i,golden[((seq-1)%3)*2048+i],1);
   commit();
  end
  passed("six_pages_exact_and_committed");
  while(published<8)#100;
  acquire(7);
  snes_addr=24'h408000;romsel_n=0;#20;read_n=0;#120;
  if(databus_oe_n)$fatal(1,"missing before reset");
  reset=1;#0.001;if(!databus_oe_n || databus_dir)$fatal(1,"reset drives stale");
  passed("reset_during_payload");
  restart(2);
  // Reset while the new autonomous producer is writing; no stale page/sequence survives.
  wait(dut.producer.offset==100);
  restart(3);
  while(published<2)#100;
  acquire(1);
  for(integer i=0;i<2048;i++)rd(24'h408000+i,golden[i],1);
  commit();passed("fresh_epoch_after_partial_production");
  // Deliberately inject a wrong producer epoch to exercise fail-stop on a protocol error.
  force dut.p_epoch=16'hfffe;
  while(!producer_fault)#100;
  release dut.p_epoch;
  if(producer_error!=3)$fatal(1,"wrong epoch fault");
  repeat(20)@(posedge queue_clk);
  if(dut.p_op!=0)$fatal(1,"fault not stopped");
  passed("injected_epoch_error_fail_stop");
  $display("PASS NES H1 PATTERN checks=%0d readbytes=%0d",checks,readbytes);
  $fclose(log);$finish;
 end
 initial begin #30000000;$fatal(1,"watchdog");end
endmodule
