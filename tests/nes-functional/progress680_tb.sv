// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module progress680_tb;
 parameter real PHASE=0;
 reg clk=0,reset=1,active=1,stop=0,ss=1,sck=0,mosi=0;
 reg [23:0] address=0;reg rn=1,wn=1,romsel=1;reg [7:0] din=0;
 wire selected,miso,oe,dir,pc,fault,sreset;wire [7:0] dout;wire [15:0] pads;
 nes_sink_bridge165 dut(.clk(clk),.raw_reset(reset),.active(active),.stop(stop),.session_release_reset(sreset),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.spi_selected(selected),.spi_miso(miso),
  .address(address),.read_n(rn),.write_n(wn),.romsel_n(romsel),.data_in(din),
  .data_out(dout),.oe_n(oe),.dir(dir),.pad_commit(pc),.pad_buttons(pads),.fault(fault));
 always #5.952 clk=~clk;
 reg [7:0] tx[0:258],rx[0:258],head[0:15],ack[0:11];
 integer checks=0;
 function automatic [7:0] c8(input [7:0] c0,b);
  reg [7:0] c;c=c0^b;repeat(8)c=c[7]?(c<<1)^7:c<<1;return c;
 endfunction
 function automatic [15:0] c16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;c=c0^{b,8'd0};repeat(8)c=c[15]?(c<<1)^16'h1021:c<<1;return c;
 endfunction
 task transfer(input integer size);
  #2000;ss=0;#2000;
  for(int k=0;k<size;k++)begin rx[k]=0;for(int b=7;b>=0;b--)begin
   mosi=tx[k][b];#190.476;sck=1;rx[k][b]=selected?miso:0;#190.476;sck=0;
  end end
  #2000;ss=1;#2000;
 endtask
 task status;
  reg [7:0] crc;
  for(int k=0;k<20;k++)tx[k]=0;tx[0]='he0;transfer(20);
  crc=0;for(int k=1;k<19;k++)crc=c8(crc,rx[k]);
  if(rx[1]!=='hf7||rx[19]!==crc)$fatal(1,"snapshot CRC");
  checks++;
 endtask
 task write_byte(input [23:0] a,input [7:0] b);
  address=a;rn=1;wn=0;din=~b;#50;din=b;#100;wn=1;#150;
 endtask
 task event_write;write_byte('h601d,'ha5);endtask
 task prepare(input [15:0] seq,input [7:0] opcode=2);
  reg [15:0] crc;
  for(int k=0;k<16;k++)head[k]=0;
  head[0]=opcode;head[1]=2;head[2]=seq[7:0];head[3]=seq[15:8];head[4]='h34;head[5]='h12;head[8]=97;
  tx[0]='he1;crc=c16('hffff,tx[0]);
  for(int k=0;k<16;k++)begin tx[k+1]=head[k];crc=c16(crc,head[k]);end
  tx[17]=crc[15:8];tx[18]=crc[7:0];
  ack[0]=opcode==3?1:0;ack[1]=opcode;
  for(int k=2;k<10;k++)ack[k]=head[k];ack[10]='h65;ack[11]='h9a;
 endtask
 task publish;
  for(int k=0;k<12;k++)write_byte('h6010+k,ack[k]);
  write_byte('h601c,'ha5);#1000;
 endtask
 task restart;
  reset=1;stop=0;active=1;ss=1;rn=1;wn=1;#200;reset=0;#1000;
 endtask
 task expect_flags(input [7:0] expected);
  status();if(rx[2]!==expected)$fatal(1,"flags got %02x expected %02x",rx[2],expected);
 endtask
 initial begin
  #(PHASE);restart();event_write();expect_flags(0);
  prepare(0);transfer(19);event_write();expect_flags(1);
  write_byte('h6010,0);event_write();expect_flags(1);
  publish();expect_flags(2);event_write();expect_flags(10);
  if(dut.endpoint.retired!==1||dut.endpoint.accepted!==1)$fatal(1,"event retired head");
  // E0 snapshot remains coherent while a real write changes the event latch.
  prepare(1);transfer(19);expect_flags(3);publish();expect_flags(2);
  fork status();begin #16000;event_write();end join
  if(rx[2]!==2)$fatal(1,"torn snapshot");expect_flags(10);
  // E1 acceptance wins even when the event pulse is forced on that exact edge.
  prepare(2);
  fork transfer(19);begin
   wait(!ss);wait(ss);wait(dut.endpoint.ss[1]&&!dut.endpoint.prev_ss);
   force dut.mp=1;@(posedge clk);#1;release dut.mp;
  end join
  expect_flags(3);publish();event_write();expect_flags(10);
  stop=1;#100;expect_flags(2);stop=0;expect_flags(2);
  event_write();expect_flags(10);
  // RUN loss cancels the lifetime including a half-written progress strobe.
  address='h601d;din='ha5;wn=0;#50;active=0;#1;if(!oe||dir)$fatal(1,"raw RUN release");
  #100;wn=1;active=1;#1000;expect_flags(0);
  // No credit leak with four immutable heads. ACK each against its own identity.
  for(int k=0;k<4;k++)begin prepare(k);transfer(19);event_write();end
  expect_flags(5);
  for(int k=0;k<4;k++)begin prepare(k);publish();event_write();end
  expect_flags(10);
  if(dut.endpoint.accepted!==4||dut.endpoint.retired!==4)$fatal(1,"four credits");
  // Counter wrap is a white-box seed; the actual E1/ACK path does the wrap.
  @(negedge clk);dut.endpoint.accepted=16'hffff;dut.endpoint.retired=16'hffff;
  prepare(4);transfer(19);publish();event_write();expect_flags(10);
  if(dut.endpoint.accepted!==0||dut.endpoint.retired!==0)$fatal(1,"counter wrap");
  prepare(5,3);transfer(19);publish();expect_flags(2);
  if(rx[7]!==1)$fatal(1,"final ACK status changed");
  // An event cannot hide identity failure or make an empty ACK legal.
  prepare(6);transfer(19);ack[8]^=1;publish();event_write();status();
  if(!fault||rx[2][3]||dut.endpoint.retired!==1)$fatal(1,"bad identity");
  restart();write_byte('h6010,0);event_write();status();
  if(!fault||rx[2][3])$fatal(1,"empty ACK became legal");
  restart();prepare(0);tx[18]^=1;transfer(19);event_write();status();
  if(!fault||rx[2][3])$fatal(1,"CRC hidden");
  $display("PASS680 checks=%0d phase=%0f",checks,PHASE);$finish;
 end
 initial begin #20000000;$fatal(1,"watchdog");end
endmodule
