// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module board134_tb;
 reg CLKIN=0,SNES_SYSCLK=0,SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 integer phase=0;
 always #62.5 CLKIN=~CLKIN;
 initial begin if($value$plusargs("PHASE_PS=%d",phase))begin end
  #(phase*0.001);forever #22.727 SNES_SYSCLK=~SNES_SYSCLK;end
 tri SPI_MISO;tri [15:0] ROM_DATA;tri [7:0] SNES_DATA,RAM_DATA;
 wire [21:0] ROM_ADDR;wire [18:0] RAM_ADDR;
 wire ROM_1CE,ROM_2CE,ROM_ZZ,ROM_OE,ROM_WE,ROM_BHE,ROM_BLE;
 wire MCU_RDY,SNES_IRQ,SNES_DATABUS_OE,SNES_DATABUS_DIR,RAM_OE,RAM_WE,DAC_MCLK,DAC_LRCK,DAC_SDOUT;
 fxpak_nes_run134_top dut(.*);
 rom_boot_model ram(.reset(dut.power_reset),.psram_address(ROM_ADDR),.psram_data(ROM_DATA),
  .psram_1ce(ROM_1CE),.psram_2ce(ROM_2CE),.psram_oe(ROM_OE),.psram_we(ROM_WE),.psram_bhe(ROM_BHE),.psram_ble(ROM_BLE));
 integer checks=0,status_reads=0,sample_events=0,actual_sample_events=0;
 reg [55:0] received,expected_snapshot;
 reg [31:0] before_count;
 task automatic ck(input bit ok,input string why);
  checks++;if(!ok)$fatal(1,"BOARD134 %s checks=%0d time=%0f",why,checks,$realtime);
 endtask
 always @(posedge SNES_SYSCLK)begin
  if(!dut.power_reset && dut.cpu_sample && !dut.core_reset)sample_events++;
  if($time>1000)begin
   ck(SNES_DATA===8'hzz && SNES_DATABUS_OE && !SNES_DATABUS_DIR,"SNES bus isolation");
   ck(RAM_DATA===8'hzz && RAM_OE && RAM_WE && ROM_ZZ,"unused memory isolation");
   ck(!(dut.boot_selected && dut.observer_selected),"SPI slave overlap");
  end
 end
 task automatic byte_io(input [7:0] tx,output [7:0] rx);
  for(integer b=7;b>=0;b--)begin
   SPI_MOSI=tx[b];#2000;SPI_SCK=1;#1;rx[b]=SPI_MISO;#1999;SPI_SCK=0;
  end
 endtask
 task automatic finish_spi;
  #2000;SPI_SS=1;#0.001;ck(SPI_MISO===1'bz,"raw CS release");#3000;
 endtask
 function automatic [7:0] crc_byte(input [7:0] old,value);
  reg [7:0] c;begin c=old^value;for(integer i=0;i<8;i++)c=c[7]?(c<<1)^8'h07:c<<1;crc_byte=c;end
 endfunction
 task automatic command(input [7:0] op,input [23:0] offset,input [7:0] arg);
  reg [7:0] b[0:7],rx,c;
  b[0]=op;b[1]=offset[23:16];b[2]=offset[15:8];b[3]=offset[7:0];b[4]=arg;b[5]=~arg;c=0;
  for(integer i=0;i<6;i++)c=crc_byte(c,b[i]);b[6]=c;b[7]=8'ha5;
  SPI_SS=0;#2000;for(integer i=0;i<8;i++)byte_io(b[i],rx);finish_spi();
 endtask
 task automatic status;
  reg [7:0] rx;
  SPI_SS=0;#2000;byte_io(8'h70,rx);
  // This is the exact transaction capture, before subsequent CPU progress.
  expected_snapshot=dut.observer.snapshot;received=0;
  for(integer i=0;i<7;i++)begin byte_io(0,rx);received={received[47:0],rx};end
  ck(received===expected_snapshot,"coherent snapshot");
  ck(received[55:48]==8'hd4,"observer identity");
  finish_spi();status_reads++;
 endtask
 initial begin
  wait(MCU_RDY);#1000;
  ck(dut.core_reset && !dut.core.run_enable,"startup held");status();
  ck(received[47:40]==1 && received[31:0]==0,"startup report");
  command(8'h60,0,0);
  for(integer a=0;a<65536;a++)ram.prg[a]=8'hea;
  for(integer a=0;a<32768;a++)ram.chr[a]=0;
  ram.prg[0]=8'h4c;ram.prg[1]=0;ram.prg[2]=8'h80;
  for(integer a=65530;a<65536;a++)ram.prg[a]=a[0]?8'h80:0;
  @(negedge dut.core.mem_clk);dut.core.loader_boot.boot.loader.loaded_bytes=81920;
  command(8'h62,81920,0);
  @(negedge dut.core.mem_clk);dut.core.loader_boot.control.verified=1;
  command(8'h63,81920,0);wait(!dut.core_reset);repeat(500)@(negedge SNES_SYSCLK);
  ck(dut.observer.samples==sample_events && sample_events>0,"actual CPU sample events");
  status();ck(received[47:40]==0 && received[31:0]>0,"RUN report");before_count=received[31:0];
  status();ck(received[31:0]>before_count,"RUN progress");
  // Truncated/foreign observer commands cannot change the loader lifecycle.
  SPI_SS=0;#2000;begin reg [7:0] rx;byte_io(8'h71,rx);byte_io(0,rx);ck(SPI_MISO===1'bz,"foreign command floats");end
  finish_spi();ck(dut.core.run_enable && !dut.core.out_spi_fault,"foreign command isolation");
  SPI_SS=0;#2000;begin reg [7:0] rx;byte_io(8'h70,rx);end
  finish_spi();ck(dut.core.run_enable && !dut.core.out_spi_fault,"truncated read isolation");
  command(8'h64,81920,0);ck(dut.core_reset && !dut.core.run_enable,"STOP through physical SPI");
  before_count=dut.observer.samples;status();ck(received[47:40]==1 && received[31:0]==before_count,"STOP retained samples");
  repeat(100)@(negedge SNES_SYSCLK);ck(dut.observer.samples==before_count,"STOP no progress");
  // Fault input injection checks observer retention only, not the ROM fault detector.
  force dut.rom_fault=1;force dut.rom_error=4'h3;repeat(3)@(negedge SNES_SYSCLK);
  release dut.rom_fault;release dut.rom_error;status();
  ck(received[47:40]==3 && received[39:32]==3,"sticky first ROM fault");
  force dut.rom_fault=1;force dut.rom_error=4'h5;repeat(3)@(negedge SNES_SYSCLK);
  release dut.rom_fault;release dut.rom_error;status();ck(received[39:32]==3,"first error retained");
  // Saturation uses a seeded counter boundary; no four-billion-event run claim.
  actual_sample_events=sample_events;
  @(negedge SNES_SYSCLK);dut.observer.samples=32'hfffffffe;
  force dut.core_reset=0;force dut.cpu_sample=1;repeat(4)@(negedge SNES_SYSCLK);
  release dut.core_reset;release dut.cpu_sample;status();ck(received[31:0]==32'hffffffff,"counter saturation");
  ck(ram.writes==0,"full write not repeated");
  $display("PASS134 status=%0d actual_sample_events=%0d injected_events=%0d checks=%0d phase_ps=%0d",status_reads,actual_sample_events,sample_events-actual_sample_events,checks,phase);$finish;
 end
 initial begin #10000000;$fatal(1,"BOARD134 watchdog");end
endmodule
