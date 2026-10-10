// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module screen144_status_late_tb;
 reg clk=0,reset=1,active=1,read_n=1,write_n=1,romsel_n=1;
 reg [23:0] address=24'h007000;reg [7:0] data_in=8'h70;
 reg SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 wire receive_write,selected,miso;
 nes_screen_status142 dut(.*);
 always #5.952 clk=~clk;
 task trial(input integer delay_ns,input [7:0] target);
  reset=1;write_n=1;data_in=8'h70;#120;reset=0;#120;
  write_n=0;#(delay_ns);data_in=target;#(160-delay_ns);write_n=1;#120;
  $display("OBS144 delay_ns=%0d target=%h observed=%h",delay_ns,target,dut.stage);
 endtask
 initial begin
  trial(0,8'h63);if(dut.stage!=8'h63)$fatal(1,"on-time control");
  trial(80,8'h63);if(dut.stage!=8'h70)$fatal(1,"late-data stale capture not reproduced");
  trial(80,8'h31);if(dut.stage!=8'h70)$fatal(1,"early-phase stale capture not reproduced");
  $display("PASS144 stale-stage reproduction; hypothesized input delay, not measured board timing");$finish;
 end
endmodule
