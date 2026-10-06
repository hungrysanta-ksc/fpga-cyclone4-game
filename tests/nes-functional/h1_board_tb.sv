// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module h1_board_tb;
 reg clock84=0,clock_enable=1,locked=0;
 always #5.952381 if(clock_enable)clock84=~clock84;
 reg SPI_MOSI=0,SPI_SS=1,SPI_SCK=0;
 wire spi_miso,spi_drive;
 reg [23:0] SNES_ADDR_IN=0;
 reg SNES_READ_IN=1,SNES_WRITE_IN=1,SNES_ROMSEL_IN=1;
 reg [7:0] snes_data_in=0;
 wire [7:0] snes_data_out;
 wire SNES_DATABUS_OE,SNES_DATABUS_DIR,run_active,diagnostic_fault;
 wire [15:0] epoch;
 nes_h1_board_bus dut(.*);
 reg [7:0] rom[0:65535],pattern[0:6143];
 integer checks=0,romreads=0,payloadreads=0,log;
 reg [7:0] ignored,reply;
 task automatic pass(input string name);checks++;$display("PASS CASE %s",name);endtask
 task automatic byte_io(input [7:0] tx,output [7:0] rx);
  rx=0;
  for(integer b=7;b>=0;b--)begin
   SPI_MOSI=tx[b];#2000;SPI_SCK=1;
   rx[b]=spi_miso;#2000;SPI_SCK=0;
  end
  #1000;
 endtask
 task automatic query(input [7:0] cmd,input [7:0] want);
  SPI_SS=0;#2000;byte_io(cmd,ignored);byte_io(0,reply);
  if(!spi_drive || reply!==want)$fatal(1,"SPI query%h got%h expected%h",cmd,reply,want);
  SPI_SS=1;#0.001;if(spi_drive)$fatal(1,"SPI SS release");#2000;
 endtask
 task automatic control(input [7:0] cmd,input [7:0] a,input [7:0] b,input integer extra=0);
  SPI_SS=0;#2000;byte_io(cmd,ignored);byte_io(a,ignored);byte_io(b,ignored);
  if(extra)byte_io(0,ignored);
  SPI_SS=1;#2000;
 endtask
 task automatic wr(input integer a,input integer value);
  SNES_ADDR_IN=a;snes_data_in=value;SNES_ROMSEL_IN=1;#20;SNES_WRITE_IN=0;
  #180;if(SNES_DATABUS_OE || SNES_DATABUS_DIR)$fatal(1,"write direction");
  SNES_WRITE_IN=1;#20;SNES_ADDR_IN=24'h123456;#100;
 endtask
 task automatic rd(input integer a,input integer want,input integer select,input integer kind=0);
  SNES_ADDR_IN=a;SNES_ROMSEL_IN=select;#20;SNES_READ_IN=0;#120;
  if(SNES_DATABUS_OE || !SNES_DATABUS_DIR || snes_data_out!==want[7:0])$fatal(1,"read%h got%h wanted%h",a,snes_data_out,want);
  #60;
  if(kind==1)romreads++;
  if(kind==2)payloadreads++;
  if(kind!=0)$fdisplay(log,"%0d %0d %0d",kind,a,snes_data_out);
  SNES_READ_IN=1;#0.001;if(!SNES_DATABUS_OE || SNES_DATABUS_DIR)$fatal(1,"read release");
  #20;SNES_ADDR_IN=24'habcd00;#100;
 endtask
 task automatic acquire(input integer seqnum);
  wr(24'h6002,epoch&255);wr(24'h6003,epoch>>8);wr(24'h6004,seqnum&255);wr(24'h6005,seqnum>>8);wr(24'h6000,1);
  while(!dut.ready && !dut.fault)#100;
  if(diagnostic_fault)$fatal(1,"acquire");
 endtask
 task automatic consume(input integer page);
  for(integer i=0;i<2048;i++)rd(24'h408000+i,pattern[page*2048+i],0,2);
  wr(24'h6000,2);while(dut.busy)#100;
  if(dut.host_read_owned || diagnostic_fault)$fatal(1,"commit");
 endtask
 initial begin
  log=$fopen("board-bytes.tsv","w");$readmemh("program-full.hex",rom);$readmemh("h1-pattern.hex",pattern);
  #100;if(!SNES_DATABUS_OE || spi_drive || run_active)$fatal(1,"unlocked drive");
  locked=1;#1000;query(8'hf0,8'ha5);query(8'hf1,8'h34);query(8'hf2,2);query(8'hf3,0);
  control(8'he8,8'ha5,0);control(8'he8,8'ha5,8'h5a,1);
  SPI_SS=0;#2000;byte_io(8'he8,ignored);byte_io(8'ha5,ignored);SPI_SS=1;#2000;
  if(run_active || epoch!=0)$fatal(1,"bad arm accepted");
  pass("identity_invalid_key_extra_and_incomplete_frame");
  control(8'he8,8'ha5,8'h5a);query(8'hf3,1);
  if(!run_active || epoch!=1)$fatal(1,"arm");
  control(8'he8,8'ha5,8'h5a);if(epoch!=1)$fatal(1,"active rearm");
  rd(24'h600b,1,1);rd(24'h600c,0,1);
  pass("arm_once_epoch_registers");
  for(integer i=0;i<65536;i++)rd(((i/32768)<<16)+24'h8000+(i%32768),rom[i],0,1);
  rd(24'h808000,rom[0],0);rd(24'h81ffff,rom[65535],0);
  SNES_ADDR_IN=24'h408000;SNES_ROMSEL_IN=1;#20;SNES_READ_IN=0;#180;
  if(!SNES_DATABUS_OE)$fatal(1,"deselected payload drive");SNES_READ_IN=1;#100;
  pass("full_64KiB_ROM_and_mirrors_bus_exclusion");
  for(integer seq=1;seq<=3;seq++)begin acquire(seq);consume(seq-1);end
  pass("three_pages_through_board_mux");
  acquire(4);SNES_ADDR_IN=24'h408000;SNES_ROMSEL_IN=0;#20;SNES_READ_IN=0;#120;
  if(SNES_DATABUS_OE)$fatal(1,"before stop");
  control(8'he9,8'ha5,8'h5a);
  if(!SNES_DATABUS_OE || SNES_DATABUS_DIR || run_active)$fatal(1,"STOP did not release");
  SNES_READ_IN=1;#100;query(8'hf3,1);
  control(8'he8,8'ha5,8'h5a);rd(24'h600b,2,1);
  while(dut.published<2)#100;
  acquire(1);consume(0);pass("stop_while_read_then_new_epoch");
  SNES_ADDR_IN=24'h008000;SNES_ROMSEL_IN=0;#20;SNES_READ_IN=0;#120;
  if(SNES_DATABUS_OE)$fatal(1,"before PLL loss");
  clock_enable=0;locked=0;#0.001;
  if(!SNES_DATABUS_OE || SNES_DATABUS_DIR || spi_drive)$fatal(1,"clock stopped PLL loss");
  #1000;SNES_READ_IN=1;clock_enable=1;locked=1;#1000;
  if(run_active)$fatal(1,"PLL relock auto restarted");
  query(8'hf3,2);control(8'he8,8'ha5,8'h5a);rd(24'h600b,3,1);
  pass("stopped_clock_lock_loss_and_explicit_rearm");
  control(8'he9,8'ha5,8'h5a);query(8'hf2,2);
  $display("PASS NES H1 BOARD checks=%0d rombytes=%0d payloadbytes=%0d",checks,romreads,payloadreads);
  $fclose(log);$finish;
 end
 initial begin #60000000;$fatal(1,"watchdog");end
endmodule
