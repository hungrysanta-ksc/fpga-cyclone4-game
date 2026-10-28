// SPDX-License-Identifier: MIT
// Actual loader prefix to full board and functional PSRAM; deliberately incomplete.
`timescale 1ns/1ps
module nrom449_tb;
 reg CLKIN=0,SNES_SYSCLK=0,SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 always #62.5 CLKIN=~CLKIN;
 initial begin #3.5;forever #22.727 SNES_SYSCLK=~SNES_SYSCLK;end
 reg [23:0] SNES_ADDR_IN=0;reg SNES_READ_IN=1,SNES_WRITE_IN=1,SNES_ROMSEL_IN=1;
 reg [7:0] host_data=0;
 tri SPI_MISO;tri [15:0] ROM_DATA;tri [7:0] SNES_DATA,RAM_DATA;
 assign SNES_DATA=!SNES_WRITE_IN?host_data:8'hzz;
 wire [21:0] ROM_ADDR;wire [18:0] RAM_ADDR;
 wire ROM_1CE,ROM_2CE,ROM_ZZ,ROM_OE,ROM_WE,ROM_BHE,ROM_BLE;
 wire MCU_RDY,SNES_IRQ,SNES_DATABUS_OE,SNES_DATABUS_DIR,RAM_OE,RAM_WE,DAC_MCLK,DAC_LRCK,DAC_SDOUT;
 fxpak_nes_screen137_top dut(.*);
 rom_boot_full_model ram(.reset(dut.power_reset),.psram_address(ROM_ADDR),.psram_data(ROM_DATA),
 .psram_1ce(ROM_1CE),.psram_2ce(ROM_2CE),.psram_oe(ROM_OE),.psram_we(ROM_WE),.psram_bhe(ROM_BHE),.psram_ble(ROM_BLE));
 function automatic [7:0] crc_byte(input [7:0] old,value);
  reg [7:0] c;begin c=old^value;for(integer i=0;i<8;i++)c=c[7]?(c<<1)^8'h07:c<<1;return c;end
 endfunction
 task automatic command(input [7:0] op,input [23:0] offset);
  reg [7:0] b[0:7],c;b[0]=op;b[1]=offset[23:16];b[2]=offset[15:8];b[3]=offset[7:0];b[4]=0;b[5]=255;c=0;
  for(integer i=0;i<6;i++)c=crc_byte(c,b[i]);b[6]=c;b[7]=8'ha5;
  SPI_SS=0;#2000;for(integer i=0;i<8;i++)for(integer bitno=7;bitno>=0;bitno--)begin SPI_MOSI=b[i][bitno];#190.476;SPI_SCK=1;#190.476;SPI_SCK=0;end
  #2000;SPI_SS=1;#3000;
 endtask
 task automatic snes_write(input [23:0] a,input [7:0] value);
  SNES_ADDR_IN=a;host_data=value;SNES_ROMSEL_IN=1;#20;SNES_WRITE_IN=0;#180;
  SNES_WRITE_IN=1;#20;SNES_ADDR_IN=24'h123456;#200;
 endtask
 task automatic snes_read_program;
  SNES_ADDR_IN=24'h008000;SNES_ROMSEL_IN=0;#20;SNES_READ_IN=0;#200;
  if(SNES_DATABUS_OE || !SNES_DATABUS_DIR || SNES_DATA!==8'h78)$fatal(1,"SNES boot program read failed %h",SNES_DATA);
  SNES_READ_IN=1;SNES_ROMSEL_IN=1;SNES_ADDR_IN=24'h123456;#200;
 endtask
 reg [7:0] tx[0:258],rx[0:258];integer block_file;
 function automatic [15:0] crc16(input [15:0] old,input [7:0] value);
  reg [15:0] c;begin c=old^{value,8'd0};for(integer i=0;i<8;i++)c=c[15]?(c<<1)^16'h1021:c<<1;return c;end
 endfunction
 task automatic transfer(input integer n);
  SPI_SS=0;#2000;
  for(integer k=0;k<n;k++)begin
   rx[k]=0;for(integer b=7;b>=0;b--)begin SPI_MOSI=tx[k][b];#190.476;SPI_SCK=1;#190.476;rx[k][b]=SPI_MISO;SPI_SCK=0;end
  end
  #2000;SPI_SS=1;#3000;
 endtask
 task automatic status_frame(input [7:0] op,input [15:0] token);
  reg [7:0] c;
  tx[0]=op;tx[1]=0;tx[2]=token[15:8];tx[3]=token[7:0];tx[4]=0;tx[5]=8'hff;c=0;
  for(integer i=0;i<6;i++)c=crc_byte(c,tx[i]);tx[6]=c;tx[7]=8'ha5;transfer(8);
 endtask
 task automatic drain_one;
  integer n;reg [15:0] token,c;
  wait(dut.core.native_spi.sealed || dut.core.native_spi.fault);
  if(dut.core.native_spi.fault)$fatal(1,"source SPI fault before first record");
  status_frame(8'hd0,0);
  if(rx[1]!==8'hd6 || !rx[2][0] || rx[2][7])$fatal(1,"D0 status %h %h",rx[1],rx[2]);
  token={rx[3],rx[4]};n={rx[5],rx[6]};if(n<1 || n>256)$fatal(1,"D0 length %0d",n);
  for(integer i=0;i<n+3;i++)tx[i]=0;tx[0]=8'hd1;transfer(n+3);
  c=16'hffff;block_file=$fopen("nrom427-block.hex","w");
  for(integer i=0;i<n;i++)begin c=crc16(c,rx[i+1]);$fwrite(block_file,"%02x\n",rx[i+1]);end
  $fclose(block_file);
  if(c!=={rx[n+1],rx[n+2]})$fatal(1,"D1 CRC mismatch");
  status_frame(8'hd2,token);status_frame(8'hd0,0);
  if(rx[1]!==8'hd6 || {rx[3],rx[4]}!==(token+16'd1) || rx[2][7])$fatal(1,"D2 retirement failed");
  $display("PASS NROM427 geometry first block token=%0d bytes=%0d crc=%h",token,n,c);
 endtask

 import "DPI-C" function void start_worker();
 import "DPI-C" function int next_request(output longint unsigned tx);
 import "DPI-C" function void submit_response(input longint unsigned rx);
 import "DPI-C" function int worker_result();
 reg [7:0] expected[0:255];
 initial begin
  longint unsigned request,response;integer pending;
  $readmemh("fixture-prg.hex",expected,0,255);
  wait(!dut.core.diagnostic_reset);repeat(20)@(negedge dut.core.mem_clk);start_worker();
  pending=next_request(request);
  while(pending==1)begin
   for(integer i=0;i<8;i++)tx[i]=request[63-i*8 -: 8];transfer(8);response=0;
   for(integer i=0;i<8;i++)response={response[55:0],rx[i]};submit_response(response);pending=next_request(request);
  end
  if(pending!=0 || worker_result()!=0)$fatal(1,"loader worker failed");
  if(dut.core.loader_boot.boot.loader.loaded_bytes!==19'd256 || dut.core.run_enable || dut.rom_fault)$fatal(1,"prefix state");
  for(integer i=0;i<256;i++)if(ram.prg[i]!==expected[i])$fatal(1,"memory mismatch %0d",i);
  if(ram.writes!=256)$fatal(1,"write count %0d",ram.writes);
  $display("PASS NROM449 actual loader full board PSRAM prefix bytes=256");$finish;
 end
 initial begin #300000000;$fatal(1,"NROM449 watchdog");end
endmodule
