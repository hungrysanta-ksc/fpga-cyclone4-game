// SPDX-License-Identifier: MIT
// Full-sized058 loader pin writes prepare the image.059 SPI reads/ACKs it.
// Direct loader command stimulus is explicit; this is not SPI DATA throughput.
`timescale 1ns/1ps
module spi_readback_pin_tb;
 reg clk=0,mem_clk=0,reset=1,read_reset=1;
 always #23.280423 clk=~clk;
 always #5.952381 mem_clk=~mem_clk;
 reg SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 wire spi_miso,spi_selected,load_ready,loaded,run_enable,boot_fault,spi_fault,rom_chr32;
 wire [3:0] boot_error,spi_error;wire [16:0] loaded_bytes;
 reg rom_request=0;reg [21:0] rom_address=0;
 wire rom_ready,rom_response,rom_error;wire [21:0] rom_response_address,psram_address;wire [7:0] rom_data;
 wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;tri [15:0] psram_data;
 nes_spi_boot dut(.*);rom_boot_model memory(.*);
 reg tb_begin=0,tb_valid=0,tb_end=0,tb_chr32=0;reg [7:0] tb_data=0;
 reg [7:0] tx[8],rx[8];integer checked=0,fd,rc,ss,sck,mosi,expectation;
 reg [63:0] delta;integer wave_mode=0;
 function automatic [7:0] value(input integer a);value=(a*73)^(a>>7)^(a>>13)^8'ha6;endfunction
 function automatic [7:0] crc_byte(input [7:0] p,input [7:0] v);
  reg [7:0] c;begin c=p^v;repeat(8)c=c[7]?(c<<1)^8'h07:c<<1;crc_byte=c;end
 endfunction
 task automatic command(input [7:0] op,input [23:0] a,input [7:0] arg);
  reg [7:0] c;
  tx[0]=op;tx[1]=a[23:16];tx[2]=a[15:8];tx[3]=a[7:0];tx[4]=arg;tx[5]=~arg;c=0;
  for(integer j=0;j<6;j++)c=crc_byte(c,tx[j]);tx[6]=c;tx[7]=8'ha5;
  SPI_SCK=0;SPI_SS=0;#120;
  for(integer j=0;j<64;j++)begin SPI_MOSI=tx[j/8][7-j%8];#60;SPI_SCK=1;#60;rx[j/8][7-j%8]=spi_miso;SPI_SCK=0;end
  #120;SPI_SS=1;#240;
 endtask
 task automatic prepare(input bit mode);
  integer total;total=mode?98304:81920;
  reset=1;SPI_SS=1;SPI_SCK=0;tb_chr32=mode;#200;reset=0;#200;
  force dut.boot.load_begin=tb_begin;force dut.boot.load_valid=tb_valid;
  force dut.boot.load_end=tb_end;force dut.boot.load_data=tb_data;force dut.boot.load_chr32=tb_chr32;
  @(negedge mem_clk);tb_begin=1;@(negedge mem_clk);tb_begin=0;
  for(integer a=0;a<total;a++)begin
   if(!load_ready)$fatal(1,"fixture load ready");tb_valid=1;tb_data=value(a);
   @(negedge mem_clk);tb_valid=0;repeat(5)@(negedge mem_clk);
  end
  tb_end=1;@(negedge mem_clk);tb_end=0;
  release dut.boot.load_begin;release dut.boot.load_valid;release dut.boot.load_end;
  release dut.boot.load_data;release dut.boot.load_chr32;
  if(!loaded||run_enable||boot_fault||spi_fault||loaded_bytes!=total)$fatal(1,"pin preparation");
 endtask
 initial begin
  if($value$plusargs("WAVE=%d",wave_mode))begin end
  if(wave_mode)begin
   prepare(0);
   fd=$fopen("waveform.txt","r");if(!fd)$fatal(1,"waveform missing");
   while(!$feof(fd))begin
    rc=$fscanf(fd,"%d %d %d %d %d\n",delta,ss,sck,mosi,expectation);
    if(rc==5)begin
     #(delta);SPI_SS=ss!=0;SPI_SCK=sck!=0;SPI_MOSI=mosi!=0;
     if(expectation>=0)begin checked++;if(spi_miso!==expectation[0])$fatal(1,"GPIO sample%0d",checked);end
    end
   end
   $fclose(fd);#1000;
   if(loaded||run_enable||spi_fault||boot_fault||memory.writes!=81920)$fatal(1,"wave STOP recovery");
   $display("PASS SPI CHECK GPIO checked_bits=%0d pin_bytes=81920 checked_bytes=32 source_failure_STOP=1",checked);
  end else begin
   for(integer mode=0;mode<2;mode++)begin
    prepare(mode!=0);command(8'h66,0,0);
    for(integer a=0;a<(mode?98304:81920);a++)begin
     command(8'h67,a,0);command(8'h6a,24'habcdef,0);
     if(rx[1]!=8'h59||rx[2]!=8'h62||rx[3]!==value(a)||{rx[4],rx[5],rx[6]}!=a||rx[7]!=0)$fatal(1,"pin CHECK byte%0d",a);
     command(8'h68,a,value(a));checked++;
     if(a%8192==8191)$display("CHECK PROGRESS mode%0d bytes%0d",mode,a+1);
    end
    command(8'h69,loaded_bytes,0);command(8'h65,0,0);
    if(rx[2]!=8'h82)$fatal(1,"finish verified");
    command(8'h63,loaded_bytes,0);read_reset=0;
    if(!run_enable)$fatal(1,"verified START");
    repeat(6)@(negedge clk);rom_address=22'h200000;rom_request=1;
    @(negedge clk);rom_request=0;wait(rom_response);#1;
    if(rom_data!==value(65536))$fatal(1,"first RUN read");
    command(8'h64,loaded_bytes,0);read_reset=1;
    if(run_enable||spi_fault||boot_fault)$fatal(1,"RUN STOP");
   end
   $display("PASS SPI CHECK FULL checked_bytes=%0d pin_bytes=%0d images=2",checked,memory.writes);
  end
  $finish;
 end
 initial begin #6000000000.0;$fatal(1,"pin CHECK watchdog");end
endmodule
