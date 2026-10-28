// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module reset451_tb;
 reg clk=0,clock_run=1,reset=1,active=0,stop=0,ss=1,sck=0,mosi=0;
 reg [23:0] address=0;reg rn=1,wn=1,romsel=1;reg [7:0] din=0;
 wire selected,miso,oe,dir,pc,fault;wire [7:0] dout;wire [15:0] pads;
 nes_sink_bridge165 dut(clk,reset,active,stop,ss,sck,mosi,selected,miso,address,rn,wn,romsel,din,dout,oe,dir,pc,pads,fault);
 always #5.952381 if(clock_run)clk=~clk;
 initial begin
  #100;reset=0;
  for(integer phase=0;phase<16;phase++)begin
   active=0;ss=0;wn=0;#(20+phase*0.375);active=1;#200;
   if(dut.host_ready||!oe||dir||selected)$fatal(1,"admitted during transaction");
   ss=1;#100;if(dut.host_ready)$fatal(1,"admitted during write");
   wn=1;#150;if(!dut.host_ready||fault)$fatal(1,"idle admission failed");
   rn=0;address=24'h400000;#50;active=0;#0.1;
   if(!oe||dir||selected||pc||dut.ready||dut.endpoint.ack_valid||dut.endpoint.used)$fatal(1,"raw cancellation");
   rn=1;#20;active=1;#150;if(!dut.host_ready)$fatal(1,"restart failed");
   @(negedge clk);clock_run=0;reset=1;#0.1;if(!oe||dir||dut.host_ready)$fatal(1,"stopped clock assertion");
   #50;reset=0;#50;if(dut.host_ready||!oe||dir)$fatal(1,"stopped clock release");
   clock_run=1;#150;if(!dut.host_ready||fault)$fatal(1,"clock restart admission");
  end
  $display("PASS NROM451 phase, raw cancel, stopped clock and idle admission");$finish;
 end
 initial begin #100000;$fatal(1,"watchdog");end
endmodule
