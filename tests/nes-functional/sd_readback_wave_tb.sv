// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module sd_readback_wave_tb;
 reg [7:0] expected[0:98303];integer check_mode=0;
 reg tb_begin=0,tb_valid=0,tb_end=0;reg [7:0] tb_data=0;

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
 always @(posedge clock84)if(nes_run_enable||run_active)$fatal(1,"Unexpected RUN");
 integer samples=0,checked=0,fd,rc,ss,sck,mosi,expectation;
 reg [63:0] delta;reg [7:0] reply;
 task automatic prepare;
  force dut.loader.boot.load_begin=tb_begin;force dut.loader.boot.load_valid=tb_valid;
  force dut.loader.boot.load_end=tb_end;force dut.loader.boot.load_data=tb_data;force dut.loader.boot.load_chr32=1'b1;
  @(negedge clock84);tb_begin=1;@(negedge clock84);tb_begin=0;
  for(integer a=0;a<98304;a++)begin
   if(!load_ready)$fatal(1,"fixture ready");tb_valid=1;tb_data=expected[a];
   @(negedge clock84);tb_valid=0;repeat(5)@(negedge clock84);
  end
  tb_end=1;@(negedge clock84);tb_end=0;
  release dut.loader.boot.load_begin;release dut.loader.boot.load_valid;release dut.loader.boot.load_end;
  release dut.loader.boot.load_data;release dut.loader.boot.load_chr32;
  if(!loaded||loaded_bytes!=98304||spi_fault||boot_fault)$fatal(1,"pin preparation");
 endtask
 task automatic legacy_query(input [7:0] op,input [7:0] expected);
  SPI_SCK=0;#2000;SPI_SS=0;#2000;
  for(integer i=0;i<16;i++)begin
   SPI_MOSI=i<8?op[7-i]:0;#2000;SPI_SCK=1;#2000;
   if(i>=8)reply[15-i]=spi_miso;
   SPI_SCK=0;
  end
  #2000;SPI_SS=1;#2000;
  if(reply!==expected)$fatal(1,"Legacy query%h got%h expected%h",op,reply,expected);
 endtask
 initial begin
  $readmemh("expected.hex",expected);
  if($value$plusargs("CHECK=%d",check_mode))begin end
  #500;locked=1;nes_reset=0;#500;
  legacy_query(8'hf0,8'ha5);legacy_query(8'hf1,8'h44);
  if(check_mode)prepare();
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
  if(memory.writes!=(check_mode?98304:256)||loaded_bytes!=0||spi_fault||boot_fault||loaded||nes_run_enable)$fatal(1,"Wave final state");
  for(integer i=0;i<256;i++)if(memory.prg[i]!==expected[i])$fatal(1,"Wave pin byte%0d",i);
  legacy_query(8'hf0,8'ha5);legacy_query(8'hf1,8'h44);
  // PLL loss invalidates the ROM path and cuts pin/MISO drive immediately.
  SPI_SS=0;#2000;locked=0;#1;
  if(spi_drive||nes_run_enable||!psram_we||!psram_oe)$fatal(1,"PLL loss gate");
  #100;locked=1;SPI_SS=1;#1000;
  if(spi_fault||loaded||loaded_bytes!=0)$fatal(1,"PLL reset did not invalidate loader");
  $display("PASS SD GPIO mode=%0d samples=%0d checked=%0d pin_bytes=%0d verified_bytes=%0d legacy_queries=%0d pll_loss=1 no_RUN=1",check_mode,samples,checked,memory.writes,check_mode?256:0,check_mode?4:6);$finish;
 end
 initial begin #600000000.0;$fatal(1,"Wave timeout");end
endmodule
