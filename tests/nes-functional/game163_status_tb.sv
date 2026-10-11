// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module game163_status_tb;
 reg clk=0,reset=1,active=0,read_n=1,write_n=1,romsel_n=1;
 reg [23:0] address=0;reg [7:0] data_in=0;
 reg SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 wire receive_write,selected,miso;
 nes_screen_status151 dut(.*);
 always #5.952 clk=~clk;
 integer checks=0;
 task automatic write_byte(input [23:0] a,input [7:0] d,input integer late);
  address=a;data_in=8'h70;read_n=1;write_n=0;
  #(late);data_in=d;#(300-late);write_n=1;address=24'h123456;data_in=8'hee;#180;
 endtask
 task automatic xbyte(input [7:0] tx,output [7:0] rx);
  for(integer i=7;i>=0;i--)begin SPI_MOSI=tx[i];#2000;SPI_SCK=1;#100;rx[i]=miso;#1900;SPI_SCK=0;end
 endtask
 reg [7:0] b[0:7];reg [7:0] code;
 task automatic observe;
  SPI_SS=0;#2000;xbyte(8'h73,b[0]);for(integer i=1;i<8;i++)xbyte(0,b[i]);#2000;SPI_SS=1;#2000;
 endtask
 initial begin
  for(integer k=0;k<6;k++)for(integer phase=0;phase<3;phase++)for(integer late=0;late<=160;late+=80)begin
   reset=1;active=0;#100;reset=0;#150;active=1;#150;#(phase*3.5);
   code=k==0?8'ha9:8'he0+k;
   write_byte(24'h007001,code,late);write_byte(24'h007000,6,late);
   write_byte(24'h007001,8'h55,late); // Existing first-nonzero byte must persist.
   active=0;#150;write_byte(24'h007001,8'h66,late);observe();
   if(b[1]!==8'he5||b[2]!==6||b[3]!==code||b[7]!==1)$fatal(1,"status not retained %h %h",code,b[3]);
   checks++;
  end
  reset=1;#100;reset=0;#150;observe();if(b[3]!==0)$fatal(1,"reset stale success");
  $display("PASS163 STATUS54codes/phases/late-data/SPI/STOP-sticky plus reset");$finish;
 end
 initial begin #30000000;$fatal(1,"watchdog");end
endmodule
