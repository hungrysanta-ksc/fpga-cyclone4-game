// SPDX-License-Identifier: MIT
// Functional actual board/core, seeded ROM and verified flag. Not a full load.
`timescale 1ns/1ps
module core_tb;
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
 rom_boot_model ram(.reset(dut.power_reset),.psram_address(ROM_ADDR),.psram_data(ROM_DATA),
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
 integer frames=0,pixels=0;reg [63:0] seen=0;reg [8:0] last_line=511,last_cycle=511;
 always @(negedge SNES_SYSCLK) if(!dut.core_reset)begin
  if(dut.pixel_line!=last_line || dut.pixel_cycle!=last_cycle)begin
   if(dut.pixel_line==1 && dut.pixel_cycle==1)frames++;
   if(frames>=3 && dut.pixel_line>=16 && dut.pixel_line<224 && dut.pixel_cycle>=2 && dut.pixel_cycle<258)begin
    if(!$isunknown(dut.pixel_color))begin seen[dut.pixel_color]=1;pixels++;end
   end
   last_line=dut.pixel_line;last_cycle=dut.pixel_cycle;
  end
 end
 initial begin
  $readmemh("fixture-prg.hex",ram.prg,0,16383);$readmemh("fixture-chr.hex",ram.chr,0,8191);
  wait(!dut.core.diagnostic_reset);repeat(20)@(negedge dut.core.mem_clk);
  dut.core.loader_boot.boot.loader.phase=16'h10;
  dut.core.loader_boot.boot.loader.loaded_bytes=19'h60000;
  dut.core.loader_boot.boot.loader.count_complete=1;
  dut.core.loader_boot.control.verified=1;
  repeat(8)@(negedge dut.core.mem_clk);command(8'h63,24'h60000);
  wait(!dut.core_reset);wait(frames>=4);#1000;
  if(pixels<1000 || $countones(seen)<2 || dut.rom_fault)$fatal(1,"core display failed frames=%0d pixels=%0d colors=%h fault=%d",frames,pixels,seen,dut.rom_fault);
  snes_read_program();
  if(!seen[6'h21])$fatal(1,"initial palette color absent");
  snes_write(24'h006002,8'h80);snes_write(24'h006003,8'h00);
  wait(frames>=6);#1000;
  if(!seen[6'h16])$fatal(1,"SNES pad did not change NES palette, seen=%h",seen);
  command(8'h64,24'h60000);#1000;
  if(!dut.core_reset || dut.core.run_enable)$fatal(1,"STOP did not reset core");
  $display("PASS NROM426 actual seeded NROM core pixel colors=%h pixels=%0d",seen,pixels);$finish;
 end
 initial begin #120000000;$fatal(1,"NROM426 watchdog frames=%0d",frames);end
endmodule
