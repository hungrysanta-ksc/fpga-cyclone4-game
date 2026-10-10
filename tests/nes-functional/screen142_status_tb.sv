// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module screen142_status_tb;
 reg clk=0,reset=1,active=0,read_n=1,write_n=1,romsel_n=1;
 reg [23:0] address=0;reg [7:0] data_in=0;
 reg SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 wire receive_write,selected,miso;
 nes_screen_status142 dut(.*);
 always #5.952 clk=~clk;
 integer checks=0;
 task automatic ck(input bit ok,input string msg);
  checks++;if(!ok)$fatal(1,"STATUS142 %s",msg);
 endtask
 task automatic write_stage(input [23:0] a,input [7:0] d);
  address=a;data_in=d;read_n=1;write_n=1;#70;write_n=0;#1;
  ck(receive_write==active,"direction for mailbox only");#159;
  write_n=1;#1;ck(!receive_write,"raw write release");#99;
 endtask
 task automatic xbyte(input [7:0] tx,output [7:0] rx);
  rx=0;
  for(integer i=7;i>=0;i--)begin
   SPI_MOSI=tx[i];#2000;SPI_SCK=1;#100;rx[i]=miso;#1900;SPI_SCK=0;
  end
 endtask
 reg [7:0] b[0:7];
 task automatic observe;
  SPI_SS=0;#2000;xbyte(8'h73,b[0]);
  for(integer i=1;i<8;i++)xbyte(0,b[i]);
  #2000;SPI_SS=1;#1;ck(!selected,"raw CS release");#2000;
 endtask
 initial begin
  #100;reset=0;#100;
  write_stage(24'h007000,1);observe();ck(b[1]==8'hd9&&b[2]==0&&b[6]==0&&b[7]==1,"inactive ignores writes");
  active=1;
  for(integer phase=0;phase<4;phase++)begin
   #(phase*3);write_stage(24'h007000,2);observe();ck(b[2]==2,"qualified phase write");
  end
  // Too-short strobe cannot satisfy two active samples; preserve prior stage.
  address=24'h007000;data_in=5;@(negedge clk);write_n=0;#2;write_n=1;#100;
  observe();ck(b[2]==2,"short write rejected");
  address=24'h00fffc;romsel_n=0;read_n=0;#160;read_n=1;#50;
  address=24'h00fffd;read_n=0;#160;read_n=1;romsel_n=1;#50;
  write_stage(24'h007000,6);write_stage(24'h007001,3);write_stage(24'h007001,7);
  observe();ck(b[2]==6&&b[3]==3&&b[4]==7&&b[5]==0&&b[6]==1,"first error/frame/vector flags");
  SPI_SS=0;#2000;xbyte(8'h73,b[0]);
  write_stage(24'h007000,6);
  for(integer i=1;i<8;i++)xbyte(0,b[i]);
  ck(b[6]==1,"snapshot frozen while milestones advance");SPI_SS=1;#3000;
  active=0;write_stage(24'h007000,1);observe();ck(b[2]==6&&b[3]==3&&b[6]==2,"STOP retains milestones");
  reset=1;#100;ck(!receive_write&&!selected,"reset isolation");reset=0;#100;observe();
  ck(b[2]==0&&b[3]==0&&b[4]==0&&b[6]==0,"configuration clears milestones");
  $display("PASS142 STATUS checks=%0d",checks);$finish;
 end
endmodule
