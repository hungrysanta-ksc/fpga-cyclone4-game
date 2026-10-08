// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module clock_observation087_tb;
 parameter integer WINDOW=8000000;
 defparam dut.observe.WINDOW=WINDOW;
 reg CLKIN=0,SNES_SYSCLK=0,clock_enable=1,ref_enable=0;
 real half=25.0;integer expected_count=1250000;
 always #62.5 if(clock_enable)CLKIN=~CLKIN;
 always begin #(half);if(ref_enable)SNES_SYSCLK=~SNES_SYSCLK;end
 reg SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 wire SPI_MISO,MCU_RDY;wire[21:0]ROM_ADDR;wire[18:0]RAM_ADDR;
 wire ROM_1CE,ROM_2CE,ROM_ZZ,ROM_OE,ROM_WE,ROM_BHE,ROM_BLE,RAM_OE,RAM_WE;
 tri[15:0]ROM_DATA;tri[7:0]RAM_DATA,SNES_DATA;
 wire SNES_IRQ,SNES_DATABUS_OE,SNES_DATABUS_DIR,DAC_MCLK,DAC_LRCK,DAC_SDOUT;
 fxpak_nes_diagnostic_top dut(.CLKIN(CLKIN),.SNES_SYSCLK(SNES_SYSCLK),
 .SNES_CIC_CLK(1'b0),.SNES_ADDR_IN(24'hffffff),.SNES_READ_IN(1'b0),.SNES_WRITE_IN(1'b0),
 .SNES_ROMSEL_IN(1'b0),.SNES_CPU_CLK_IN(1'b0),.SNES_REFRESH(1'b0),
 .SNES_PA_IN(8'hff),.SNES_PARD_IN(1'b0),.SNES_PAWR_IN(1'b0),.*);
 task automatic parked;
  if({ROM_1CE,ROM_2CE,ROM_OE,ROM_WE,ROM_BHE,ROM_BLE,ROM_ZZ,RAM_OE,RAM_WE,SNES_DATABUS_OE}!==10'h3ff ||
    ROM_ADDR!==0||RAM_ADDR!==0||ROM_DATA!==16'hzzzz||RAM_DATA!==8'hzz||SNES_DATA!==8'hzz||SNES_DATABUS_DIR!==0)
    $fatal(1,"MEMORY_NOT_PARKED");
 endtask
 always @(negedge CLKIN)parked();
 task automatic begin_spi;SPI_SS=0;#2000;endtask
 task automatic end_spi;#2000;SPI_SS=1;#2000;if(SPI_MISO!==1'bz)$fatal(1,"MISO_NOT_RELEASED");endtask
 task automatic xfer(input[7:0]tx,output[7:0]rx);
  rx=0;
  for(integer b=7;b>=0;b=b-1)begin
   SPI_MOSI=tx[b];#2000;SPI_SCK=1;#1000;rx[b]=SPI_MISO;#1000;SPI_SCK=0;
  end
  #2000;
 endtask
 reg[7:0]rx,bytes_read[0:16];reg[31:0]before_sequence,c;
 task automatic snapshot_read;
  begin_spi();xfer(8'hc0,rx);
  for(integer i=0;i<17;i=i+1)xfer(0,bytes_read[i]);
  end_spi();
  if(bytes_read[0]!==8'h87||{bytes_read[13],bytes_read[12],bytes_read[11],bytes_read[10]}!==32'(WINDOW)||
    bytes_read[14]!==16||bytes_read[15]!==0||bytes_read[16]!==0)$fatal(1,"SNAPSHOT_FRAMING");
 endtask
 initial begin
  if($value$plusargs("HALF=%f",half))begin end
  if($value$plusargs("COUNT=%d",expected_count))begin end
  #20000;snapshot_read();
  if(bytes_read[1][0]||bytes_read[1][1])$fatal(1,"ABSENT_REFERENCE_FALSE_VALID");
  begin_spi();xfer(8'hcf,rx);xfer(0,rx);if(rx!==8'h87)$fatal(1,"ID_MISMATCH");end_spi();
  ref_enable=1;
  wait(dut.observe.window_sequence==2);#1000;snapshot_read();
  c={bytes_read[9],bytes_read[8],bytes_read[7],bytes_read[6]};
  if(!bytes_read[1][0]||!bytes_read[1][1]||bytes_read[1][3]||c<expected_count-2||c>expected_count+2)
   $fatal(1,"FREQUENCY_WINDOW_MISMATCH count=%0d expected=%0d flags=%h",c,expected_count,bytes_read[1]);
  // Begin before publication, read sequence AFTER it: all fields must stay
  // from the command's snapshot even when a new window completes mid-frame.
  wait(dut.observe.cycles==WINDOW-600);before_sequence=dut.observe.window_sequence;snapshot_read();
  if({bytes_read[5],bytes_read[4],bytes_read[3],bytes_read[2]}!==before_sequence)$fatal(1,"TORN_SNAPSHOT");
  ref_enable=0;#20000;snapshot_read();
  if(bytes_read[1][1]||!bytes_read[1][2])$fatal(1,"STOP_NOT_OBSERVED");
  ref_enable=1;#20000;snapshot_read();if(!bytes_read[1][1]||!bytes_read[1][2])$fatal(1,"RESUME_LOST_HISTORY");
  // Incomplete bytes, unknown/start/load commands and >63 bytes cannot enable
  // any bus or wrap around to a fresh command/snapshot.
  begin_spi();SPI_MOSI=1;repeat(3)begin #2000;SPI_SCK=1;#2000;SPI_SCK=0;end end_spi();
  for(integer i=0;i<256;i=i+1)if(i!=8'hc0&&i!=8'hcf)begin
   begin_spi();xfer(i,rx);xfer(8'ha5,rx);if(rx!==0)$fatal(1,"UNKNOWN_COMMAND");xfer(8'h5a,rx);end_spi();
  end
  begin_spi();xfer(8'hc0,rx);for(integer i=0;i<70;i=i+1)begin xfer(8'hc0,rx);if(i>=16&&rx!==0)$fatal(1,"OVERREAD_WRAPPED");end end_spi();
  if(WINDOW<8000000)begin
   ref_enable=0;before_sequence=dut.observe.window_sequence;
   wait(dut.observe.window_sequence==before_sequence+2);snapshot_read();
   if(bytes_read[1][1:0]!==2'b01||!bytes_read[1][3]||{bytes_read[9],bytes_read[8],bytes_read[7],bytes_read[6]}!==0)
    $fatal(1,"ABSENT_COMPLETED_WINDOW");
   ref_enable=1;before_sequence=dut.observe.window_sequence;
   wait(dut.observe.window_sequence==before_sequence+2);snapshot_read();
   if(bytes_read[1][1:0]!==2'b11||bytes_read[1][3]||!bytes_read[1][2])$fatal(1,"RECOVERED_WINDOW_FLAGS");
   $display("PASS ABSENT_AND_RECOVERED_WINDOWS087");
  end
  // Both clocks stopped: hard-wired memory parking does not require a clock.
  clock_enable=0;ref_enable=0;SPI_SS=0;#10000;parked();SPI_SS=1;#10000;parked();
  if(SPI_MISO!==1'bz)$fatal(1,"STOPPED_CLOCK_MISO_RELEASE");
  $display("PASS OBSERVATION087 count=%0d commands=254 coherent=1 both_halt_parked=1",c);$finish;
 end
 initial begin #4000000000.0;$fatal(1,"TEST_TIMEOUT");end
endmodule
