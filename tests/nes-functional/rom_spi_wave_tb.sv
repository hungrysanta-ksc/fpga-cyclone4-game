// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module rom_spi_wave_tb;
 reg nes_clk=0,clock84=0,nes_reset=1,locked=0,read_reset=0;
 always #23.280423 nes_clk=~nes_clk;
 always #5.952381 clock84=~clock84;
 reg SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 wire spi_miso,spi_drive,load_ready,loaded,nes_run_enable,boot_fault,spi_fault;
 wire [3:0] boot_error,spi_error;wire [16:0] loaded_bytes;
 reg rom_request=0;reg [21:0] rom_address=0;wire rom_ready,rom_response,rom_error;
 wire [21:0] rom_response_address,psram_address;wire [7:0] rom_data;
 wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;wire [15:0] psram_data;
 wire [7:0] snes_data_out;wire SNES_DATABUS_OE,SNES_DATABUS_DIR,run_active,diagnostic_fault;wire [15:0] epoch;
 nes_h1_spi_boot dut(.*,.SNES_ADDR_IN(24'd0),.SNES_READ_IN(1'b1),.SNES_WRITE_IN(1'b1),.SNES_ROMSEL_IN(1'b1),.snes_data_in(8'd0));
 rom_boot_model memory(.reset(nes_reset||!locked),.*);
 integer samples=0,checked=0,fd,rc,ss,sck,mosi,expectation;
 reg [63:0] delta;reg [7:0] reply;
 task automatic legacy_query(input [7:0] op,input [7:0] expected);
  SPI_SS=0;#2000;
  for(integer i=0;i<16;i++)begin
   SPI_MOSI=i<8?op[7-i]:0;#2000;SPI_SCK=1;#2000;
   if(i>=8)reply[15-i]=spi_miso;
   SPI_SCK=0;
  end
  #2000;SPI_SS=1;#2000;
  if(reply!==expected)$fatal(1,"Legacy query%h got%h expected%h",op,reply,expected);
 endtask
 initial begin
  #500;locked=1;nes_reset=0;#500;
  legacy_query(8'hf0,8'ha5);legacy_query(8'hf1,8'h44);
  fd=$fopen("waveform.txt","r");if(!fd)$fatal(1,"waveform missing");
  while(!$feof(fd))begin
   rc=$fscanf(fd,"%d %d %d %d %d\n",delta,ss,sck,mosi,expectation);
   if(rc==5)begin
    #(delta);SPI_SS=ss!=0;SPI_SCK=sck!=0;SPI_MOSI=mosi!=0;
    if(expectation>=0)begin
     checked++;if(spi_miso!==expectation[0])$fatal(1,"MCU sample%0d got%b expected%0d",samples,spi_miso,expectation);
    end
    if(expectation!=-1)samples++;
   end
  end
  $fclose(fd);#1000;
  if(memory.writes!=64||loaded_bytes!=0||!spi_fault||spi_error!=2||nes_run_enable)$fatal(1,"Wave final state");
  for(integer i=0;i<64;i++)if(memory.prg[i]!==((i^8'ha5)&255))$fatal(1,"Wave pin byte%0d",i);
  legacy_query(8'hf0,8'ha5);legacy_query(8'hf1,8'h44);
  // PLL loss invalidates the ROM path and cuts pin/MISO drive immediately.
  SPI_SS=0;#2000;locked=0;#1;
  if(spi_drive||nes_run_enable||!psram_we||!psram_oe)$fatal(1,"PLL loss gate");
  #100;locked=1;SPI_SS=1;#1000;
  if(spi_fault||loaded||loaded_bytes!=0)$fatal(1,"PLL reset did not invalidate loader");
  $display("PASS SPI MCU WAVE samples=%0d checked=%0d pin_bytes=64 legacy_queries=4 pll_loss=1",samples,checked);$finish;
 end
 initial begin #200000000;$fatal(1,"Wave timeout");end
endmodule
