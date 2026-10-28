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
 always @(posedge dut.core.clk) if(dut.core.native_export.state==0 && dut.core.native_frame_owned)begin
  $display("DIAG export valid=%b errors=%h obs=%h rows=%0d groups=%0d objects=%0d exceptions=%0d palettes=%0d patches=%0d leasefault=%b",dut.core.native_geometry_valid,dut.core.native_errors,dut.core.native_observe_errors180,dut.core.native_row_count,dut.core.native_group_count,dut.core.native_object_count,dut.core.native_exception_count,dut.core.native_palette_count,dut.core.native_patch_count181,dut.core.lease_fault204);
  $display("DIAG members fetch=%b/%b/%h compact=%b/%b/%h raster=%b/%b/%h patch=%b/%b/%h mask=%h ce=%b",dut.core.native_frame.frame.fetch_owned,dut.core.native_frame.frame.fetch_valid,dut.core.native_frame.frame.fetch_errors,dut.core.native_frame.frame.compact_owned,dut.core.native_frame.frame.compact_valid,dut.core.native_frame.frame.compact_errors,dut.core.native_frame.frame.raster_owned,dut.core.native_frame.frame.raster_valid,dut.core.native_frame.frame.raster_errors,dut.core.native_frame.frame.patch_owned,dut.core.native_frame.frame.patch_valid,dut.core.native_frame.frame.patch_errors,dut.core.native_display_mask,dut.core.tap_ce);
 end
 integer frames=0,pixels=0;reg [63:0] seen=0;reg [8:0] last_line=511,last_cycle=511;
 always @(negedge SNES_SYSCLK) if(!dut.core_reset)begin
  if(dut.pixel_line!=last_line || dut.pixel_cycle!=last_cycle)begin
   if(dut.pixel_line==1 && dut.pixel_cycle==1)begin
    frames++;
    $display("DIAG frame=%0d source=%b rom=%b write=%b epoch=%h owned=%b valid=%b errors=%h obs=%h leasefault=%b exporterr=%h exportstate=%h sealed=%b used=%0d",frames,dut.core.source_ready204,dut.core.source_rom204,dut.core.source_write204,dut.core.source_epoch204,dut.core.native_frame_owned,dut.core.native_geometry_valid,dut.core.native_errors,dut.core.native_observe_errors180,dut.core.lease_fault204,dut.core.native_export_error,dut.core.native_export_state177,dut.core.native_spi.sealed,dut.core.native_spi.used);
   end
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
  dut.core.loader_boot.content_lifetime.serial=1;
  repeat(8)@(negedge dut.core.mem_clk);command(8'h63,24'h60000);
  wait(!dut.core_reset);wait(frames>=4);#1000;

  if(pixels<1000 || $countones(seen)<2 || dut.rom_fault)$fatal(1,"core display failed frames=%0d pixels=%0d colors=%h fault=%d",frames,pixels,seen,dut.rom_fault);
  snes_read_program();
  if(!seen[6'h21])$fatal(1,"initial palette color absent");
  snes_write(24'h006002,8'h80);snes_write(24'h006003,8'h00);
  wait(frames>=6);#1000;
  if(!seen[6'h16])$fatal(1,"SNES pad did not change NES palette, seen=%h",seen);
  if(!dut.core.native_spi.sealed)$display("DIAG pre-drain initialized=%b active=%b owned=%b valid=%b errors=%h obs=%h leasefault=%b exporterr=%h exportstate=%h",dut.core.native_initialized,dut.core.native_active,dut.core.native_frame_owned,dut.core.native_geometry_valid,dut.core.native_errors,dut.core.native_observe_errors180,dut.core.lease_fault204,dut.core.native_export_error,dut.core.native_export_state177);
  drain_one();
  command(8'h64,24'h60000);#1000;
  if(!dut.core_reset || dut.core.run_enable)$fatal(1,"STOP did not reset core");
  $display("PASS NROM426 actual seeded NROM core pixel colors=%h pixels=%0d",seen,pixels);$finish;
 end
 initial begin #105000000;$fatal(1,"NROM426 watchdog frames=%0d",frames);end
endmodule
