// SPDX-License-Identifier: MIT
// Optional instrumentation for wire-level E8 recovery and the two stopped clocks.
task status570(input int count,input bit failed);
 reg [7:0] rx[0:19],tmp,c;
 ss=0;#80000;
 for(int i=0;i<20;i++)begin
  tmp=i==0?8'he8:0;
  for(int j=7;j>=0;j--)begin
   mosi=tmp[j];#190476;sck=1;rx[i][j]=dut.spi_selected?dut.spi_miso:0;#190476;sck=0;
  end
 end
 #80000;ss=1;#200000;c=0;
 for(int i=1;i<=18;i++)begin
  c^=rx[i];for(int j=0;j<8;j++)c=c[7]?(c<<1)^8'h07:c<<1;
 end
 if({rx[1],rx[2]}!==16'hd704||rx[3][7]!==failed||rx[3][0]!==!failed||
    {rx[4],rx[5]}!==count[15:0]||rx[19]!==c)$fatal(1,"E8 after E9 flags=%h count=%d CRC=%h/%h",rx[3],{rx[4],rx[5]},rx[19],c);
 $display("E8570 flags=%h count=%0d",rx[3],count);
endtask
task external_stop570;
 wait(dut.pv&&dut.pr);
 @(negedge host_clk);host_on=0;nes_on=0;#100;reset=1;#1;quiet_plan();
 reset=0;#200000;quiet_plan();
 host_on=1;repeat(8)@(negedge host_clk);
 if(dut.transport.word_valid||dut.pv||dut.endpoint.accepted!=0)$fatal(1,"old plan after reset");
 nes_on=1;repeat(16)@(negedge nes_clk);status570(0,0);
endtask
