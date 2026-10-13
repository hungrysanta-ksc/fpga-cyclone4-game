// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Actual physical top and peripheral RTL, core lifecycle replaced by a stub.
module sink_board165_tb;
 reg host=0,nes=0;always #5.952 host=~host;always #22.727 nes=~nes;
 reg ss=1,sck=0,mosi=0,rn=1,wn=1,rs=1;reg [23:0] address=0;
 reg drive=0;reg [7:0] data=0;wire [7:0] snes_data;assign snes_data=drive?data:8'hzz;
 wire miso,oe,dir,ram_we,ram_oe,dac;wire [18:0] ram_addr;wire [7:0] ram_data;
 fxpak_nes_screen137_top dut(.CLKIN(host),.SNES_SYSCLK(nes),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.SPI_MISO(miso),
  .SNES_ADDR_IN(address),.SNES_READ_IN(rn),.SNES_WRITE_IN(wn),.SNES_ROMSEL_IN(rs),.SNES_DATA(snes_data),
  .SNES_DATABUS_OE(oe),.SNES_DATABUS_DIR(dir),.RAM_ADDR(ram_addr),.RAM_OE(ram_oe),.RAM_WE(ram_we),.RAM_DATA(ram_data),.DAC_MCLK(dac));
 reg [7:0] tx[0:258],rx[0:258];integer i,j,checks=0,dac_edges=0;reg [15:0] crc;
 realtime half_sck=190.476;
 always @(posedge dac)dac_edges++;
 function automatic [15:0] c16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;integer k;begin c=c0^{b,8'd0};for(k=0;k<8;k++)c=c[15]?(c<<1)^16'h1021:c<<1;c16=c;end
 endfunction
 task transfer(input integer count);
  integer b,k;begin ss=0;#2000;
   for(k=0;k<count;k++)begin rx[k]=0;for(b=7;b>=0;b--)begin mosi=tx[k][b];#(half_sck);sck=1;rx[k][b]=miso;#(half_sck);sck=0;end end
   #2000;ss=1;#1;if(miso!==1'bz)$fatal(1,"raw MISO release");#1999;checks++;
  end
 endtask
 task write_byte(input [23:0] a,input [7:0] v);
  begin address=a;drive=1;data=v;rn=1;wn=0;#150;wn=1;#100;drive=0;end
 endtask
 task read_byte(input [23:0] a,input [7:0] v);
  begin address=a;rn=0;wn=1;rs=1;#100;if(oe||!dir||snes_data!==v)$fatal(1,"read %h got %h expected %h",a,snes_data,v);rn=1;#100;checks++;end
 endtask
 initial begin
  #500;
  for(j=0;j<5;j++)begin
   for(i=0;i<16;i++)tx[i]=0;
   case(j)0:tx[0]=8'h73;1:tx[0]=8'h70;2:tx[0]=8'he0;3:tx[0]=8'h60;4:tx[0]=8'hd0;endcase
   half_sck=j==1?2000.0:190.476;transfer(j==2?16:8);
   case(j)0:if(rx[1]!=8'he6||rx[7]!=2)$fatal(1,"paired status");
    1:if(rx[1]!=8'he5)$fatal(1,"164 observer route");
    2:if(rx[1]!=8'hf6||rx[2]!=0)$fatal(1,"sink route");
    3,4:if(rx[1]!==0)$fatal(1,"core route");endcase
  end
  // One complete empty BEGIN packet, then the actual SNES ACK bus path.
  for(i=0;i<19;i++)tx[i]=0;tx[0]=8'he1;tx[1]=1;tx[5]=1;crc=16'hffff;
  for(i=0;i<17;i++)crc=c16(crc,tx[i]);tx[17]=crc[15:8];tx[18]=crc[7:0];transfer(19);
  read_byte(24'h006000,1);read_byte(24'h006004,16);read_byte(24'h400000,1);
  for(i=0;i<12;i++)write_byte(24'h006010+i,i);write_byte(24'h00601c,8'ha5);
  for(i=0;i<16;i++)tx[i]=0;tx[0]=8'he0;transfer(16);if(rx[2]!=2)$fatal(1,"ACK through board");
  for(i=0;i<12;i++)if(rx[3+i]!=i)$fatal(1,"ACK %0d",i);
  write_byte(24'h006002,8'h80);write_byte(24'h006003,8'h04);#500;
  if(dut.pad.current_buttons!==8'h21)$fatal(1,"pad mapping/CDC %h",dut.pad.current_buttons);
  dut.core.test_fault=1;#100;read_byte(24'h006001,8'h80);dut.core.test_fault=0;
  dut.core.test_native_fault=1;read_byte(24'h006001,8'h80);dut.core.test_native_fault=0;
  // An unexpected simultaneous SPI selection must not drive the board pin.
  force dut.boot_selected=1;force dut.sink_selected=1;#1;if(miso!==1'bz)$fatal(1,"overlap drove MISO");release dut.boot_selected;release dut.sink_selected;
  dut.core.test_run=0;#100;if(!oe||dir)$fatal(1,"STOP bus release");
  dut.core.test_run=1;#100;read_byte(24'h006000,0);
  if(ram_we!==1||ram_oe!==1||ram_addr!==0||ram_data!==8'hzz)$fatal(1,"save SRAM touched");
  if(dac_edges<100)$fatal(1,"DAC clock disconnected");
  $display("PASS SINKBOARD165 checks=%0d dac_edges=%0d",checks,dac_edges);$finish;
 end
 initial begin #3000000;$fatal(1,"board watchdog");end
endmodule
