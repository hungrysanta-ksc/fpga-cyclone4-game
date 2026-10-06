// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module h1_spi_wave_tb;
 reg clock84=0;
 always #5.952380952 clock84=~clock84;
 reg locked=0,SPI_MOSI=0,SPI_SS=1,SPI_SCK=0;
 wire spi_miso,spi_drive;
 reg [23:0] SNES_ADDR_IN=0;
 reg SNES_READ_IN=1,SNES_WRITE_IN=1,SNES_ROMSEL_IN=1;
 reg [7:0] snes_data_in=0;
 wire [7:0] snes_data_out;
 wire SNES_DATABUS_OE,SNES_DATABUS_DIR,run_active,diagnostic_fault;
 wire [15:0] epoch;
 nes_h1_board_bus dut(.*);
 integer fd,matched,ss,sck,mosi,expect_bit,samples=0,rows=0,verified=0;
 real delta;
 initial begin
  fd=$fopen("waveform.txt","r");if(!fd)$fatal(1,"waveform missing");
  locked=1;
  while(!$feof(fd))begin
   matched=$fscanf(fd,"%f %d %d %d %d\n",delta,ss,sck,mosi,expect_bit);
   if(matched==5)begin
    #(delta);SPI_SS=ss;SPI_SCK=sck;SPI_MOSI=mosi;rows++;
    if(expect_bit>=0)begin
     if(!spi_drive || spi_miso!==expect_bit[0])
      $fatal(1,"SPI sample mismatch sample=%0d expected=%0d got=%0d time=%0t",samples,expect_bit,spi_miso,$time);
     verified++;
    end
    if(expect_bit>=0 || expect_bit==-2)samples++;
   end
  end
  #1000;
  if(samples!=224 || verified!=88 || run_active || epoch!=1 || !SNES_DATABUS_OE || spi_drive)
   $fatal(1,"final C lifecycle state samples=%0d run=%0d epoch=%0d",samples,run_active,epoch);
  $display("PASS C SPI WAVE samples=%0d verified=%0d rows=%0d",samples,verified,rows);$finish;
 end
 initial begin #10000000;$fatal(1,"timeout");end
endmodule
