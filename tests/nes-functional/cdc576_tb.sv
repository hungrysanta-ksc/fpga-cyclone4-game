// SPDX-License-Identifier: MIT
`timescale 1ps/1ps
module cdc576_tb;
 reg clk=0,clock_on=1,reset=1,active=1;
 always #5952 if(clock_on)clk=!clk;
 wire host_clk=clk;
 reg nes_clk=0,pad_commit=0,pad_strobe=1,pad_read=0;
 always #23281 if(clock_on)nes_clk=!nes_clk;
 wire pad_ready,pad_serial,pad_trace;
 wire [7:0] pad_buttons;
 reg core_reset=1,rom_fault=0;
 reg [1:0] sink_rom_fault;
 @FAULT_BLOCK@
 nes_game_pad150 pad(.host_clk(clk),.nes_clk(nes_clk),.reset(core_reset),.commit(pad_commit),
  .snes_buttons(16'ha580),.host_ready(pad_ready),.strobe(pad_strobe),.read_clock(pad_read),
  .serial(pad_serial),.trace_valid(pad_trace),.trace_buttons(pad_buttons));
 reg ss=1,sck=0,mosi=0,rd=1,wr=1;
 reg [23:0] address=0;
 reg [7:0] data=0;
 reg drive=0,jitter=0;
 integer noise=0;
 always @(negedge clk)begin noise++;if(jitter&&noise%3)drive=!drive;end
 wire selected,miso,receive_write;
 wire [7:0] sink_data;
 wire sink_oe,sink_dir;
 nes_screen_status151 status(.clk(clk),.reset(reset),.active(active),.address(address),
  .read_n(rd),.write_n(wr),.romsel_n(1'b1),.data_in(data),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.bus_drive(drive),
  .selected(selected),.miso(miso),.receive_write(receive_write));
 nes_sink_bridge165 sink(.clk(clk),.raw_reset(core_reset),.active(active),.stop(sink_rom_fault[1]),
  .session_release_reset(host_cancel_reset),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),
  .address(address),.read_n(rd),.write_n(wr),.romsel_n(1'b1),.data_in(data),
  .data_out(sink_data),.oe_n(sink_oe),.dir(sink_dir));
 nes_sink_bridge165_ref old_sink(.clk(clk),.raw_reset(core_reset),.active(active),.stop(sink_rom_fault[1]),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.address(address),.read_n(rd),.write_n(wr),
  .romsel_n(1'b1),.data_in(data));
 reg [1:0] history=0;
 integer captures=0,changed=0,restarts=0;
 reg sampled;
 always @(posedge clk or posedge reset)begin
  if(reset)history<=0;
  else begin
   if(!status.ss_sync[1]&&status.sck_sync[1]&&!status.sck_previous&&status.bit_count==7&&status.byte_count==0)begin
    sampled=history[1];if(sampled!=drive)changed++;
    #1;if(status.snapshot[31]!==sampled)$fatal(1,"diagnostic captured first-stage/raw bit");
    captures++;
   end
   history<={history[0],drive};
  end
 end
 task byte_spi(input [7:0] tx,output [7:0] rx);
  for(integer n=7;n>=0;n--)begin
   mosi=tx[n];#190476;sck=1;#100;rx[n]=miso;#190376;sck=0;
  end
 endtask
 reg [7:0] reply[0:7];
 task observe;
  ss=0;#2000000;byte_spi(8'h73,reply[0]);
  for(integer n=1;n<8;n++)byte_spi(0,reply[n]);
  #2000000;ss=1;#2000000;
  if(reply[1]!==8'he6||reply[7]!==3)$fatal(1,"SPI73 version");
 endtask
 task abort_restart(input integer phase,input bit held);
  @(negedge clk);#(phase);clock_on=0;#100;core_reset=1;reset=1;rom_fault=1;
  #1;if(sink.host_ready!==0||host_cancel_reset!==1||sink_rom_fault!==0||!sink_oe||sink_dir||pad.host_release!==0)
    $fatal(1,"stopped-clock asynchronous kill");
  ss=!held;wr=!held;core_reset=0;reset=0;rom_fault=0;
  #50000;if(sink.host_ready||!host_cancel_reset||sink_rom_fault)$fatal(1,"no-clock release");
  clock_on=1;
  repeat(2)begin @(posedge clk);#1;if(sink.host_ready)$fatal(1,"premature host admission");end
  if(!held)begin
   for(integer edge_n=3;edge_n<=5;edge_n++)begin
    @(posedge clk);#1;
    if(old_sink.host_ready!==1||sink.host_ready!==(edge_n==5))$fatal(1,"admission latency reference3/candidate5");
   end
  end
  if(held)begin
   repeat(12)@(negedge clk);
   if(sink.host_ready)$fatal(1,"old transaction admitted");
   ss=1;wr=1;
  end
  repeat(6)@(negedge clk);
  if(!sink.host_ready||host_cancel_reset||sink_rom_fault)$fatal(1,"local release recovery");
  restarts++;
 endtask
 initial begin
  if($test$plusargs("SHIFT"))#7100;
  #50000;reset=0;core_reset=0;#200000;
  for(integer k=0;k<16;k++)begin
   jitter=0;drive=k[0];#50000;observe();
   if(reply[4][7]!==k[0])$fatal(1,"stable diagnostic SPI value");
   jitter=1;observe();
  end
  jitter=0;
  for(integer k=0;k<32;k++)begin abort_restart(k*173,0);abort_restart(k*173,1);end
  @(negedge clk);pad_commit=1;@(negedge clk);pad_commit=0;
  repeat(20)@(negedge nes_clk);
  if(!pad_ready)$fatal(1,"pad acknowledgement after reset");
  pad_strobe=0;repeat(3)@(negedge nes_clk);
  for(integer k=0;k<8;k++)begin
   if(pad_serial!==((8'ha7>>k)&1))$fatal(1,"pad bit after common reset");
   pad_read=1;repeat(3)@(negedge nes_clk);pad_read=0;repeat(3)@(negedge nes_clk);
  end
  if(pad_buttons!==8'ha7)$fatal(1,"pad trace after reset");
  // Fault sampling retains its two host-clock delay after admission.
  @(negedge clk);rom_fault=1;
  @(posedge clk);#1;if(sink_rom_fault[1])$fatal(1,"fault sampled prematurely");
  @(posedge clk);#1;if(!sink_rom_fault[1])$fatal(1,"fault not propagated");
  if(captures!=32||changed==0||restarts!=64)$fatal(1,"coverage captures=%0d changed=%0d restarts=%0d",captures,changed,restarts);
  $display("PASS576 captures=%0d changed=%0d restarts=%0d",captures,changed,restarts);$finish;
 end
 initial begin #(64'd10000000000);$fatal(1,"watchdog");end
endmodule
