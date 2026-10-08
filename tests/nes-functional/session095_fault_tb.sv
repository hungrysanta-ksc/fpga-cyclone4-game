// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module session095_fault_tb;
 reg board8=0,locked=0,SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 always #62.5 board8=~board8;
 reg reference20=0;always #25 reference20=~reference20;
 wire [15:0] psram_data;wire [7:0] snes_bus,ram_bus;
 wire [21:0] psram_address;wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;
 wire spi_miso,mcu_ready,rom_zz,ram_oe,ram_we,snes_irq,bus_oe,bus_dir;
 fxpak_nes_diagnostic_top dut(.CLKIN(board8),.SNES_CIC_CLK(1'b0),
 .SNES_ADDR_IN(24'd0),.SNES_READ_IN(1'b1),.SNES_WRITE_IN(1'b1),.SNES_ROMSEL_IN(1'b1),
 .SNES_CPU_CLK_IN(1'b0),.SNES_REFRESH(1'b0),.SNES_SYSCLK(reference20),.SNES_PA_IN(8'd0),.SNES_PARD_IN(1'b1),.SNES_PAWR_IN(1'b1),
 .SNES_DATA(snes_bus),.SNES_IRQ(snes_irq),.SNES_DATABUS_OE(bus_oe),.SNES_DATABUS_DIR(bus_dir),
 .SPI_MOSI(SPI_MOSI),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MISO(spi_miso),.MCU_RDY(mcu_ready),
 .ROM_ADDR(psram_address),.ROM_1CE(psram_1ce),.ROM_2CE(psram_2ce),.ROM_ZZ(rom_zz),
 .ROM_OE(psram_oe),.ROM_WE(psram_we),.ROM_BHE(psram_bhe),.ROM_BLE(psram_ble),.ROM_DATA(psram_data),
 .RAM_ADDR(),.RAM_OE(ram_oe),.RAM_WE(ram_we),.RAM_DATA(ram_bus),.DAC_MCLK(),.DAC_LRCK(),.DAC_SDOUT());
 rom_boot_model memory(.reset(!locked||!dut.clock_allowed),.*);
 initial force dut.locked=locked;
 integer total=81920,limit_frames=0,mask_link=1,park_legacy=0,frames=0,reads=0,pin_writes=0,data_frames=0,acks=0,ends=0,finishes=0,stops=0,checked=0;
 reg link_clocks=1;
 // Only the unused, reset-held H1 transport ports are parked. Its reset
 // remains asserted and epoch/address inputs constant. SPI and memory clocks
 // are independent; never mask the8MHz clock or an active memory transaction.
 initial begin
  if($value$plusargs("MASK_LINK=%d",mask_link))begin end
 end
 always @(dut.boundary.run_active or dut.boundary.nes_run_enable)
  if(dut.boundary.run_active||dut.boundary.nes_run_enable)$fatal(1,"095 unexpected RUN");
 always @(posedge psram_we)if(locked&&(!psram_1ce ^ !psram_2ce))begin
  if({psram_address,psram_1ce,1'b0}!==((pin_writes<65536?pin_writes:22'h200000+pin_writes-65536)&22'h3ffffe)||
     psram_bhe!==pin_writes[0]||psram_ble!==!pin_writes[0])$fatal(1,"095 physical write address/lane at%0d",pin_writes);
  pin_writes++;
 end
 always @(negedge psram_oe)if(locked)begin
  if(!psram_we||!(!psram_1ce ^ !psram_2ce))$fatal(1,"095 read ownership");
  if({psram_address,psram_1ce,1'b0}!==((reads<65536?reads:22'h200000+reads-65536)&22'h3ffffe))
   $fatal(1,"095 physical read address at%0d",reads);
  // The existing reader enables the complete16-bit word, then chooses the
  // requested byte internally. Byte-write strobes do not apply to reads.
  if(psram_bhe!==1'b0||psram_ble!==1'b0)$fatal(1,"095 physical read word enables at%0d",reads);
  reads++;
 end
 integer fd,rc,kind,ss,sck,mosi,sample_value,rows=0,faults=0,compared=0,keep_lock=0;
 longint unsigned event_ns;realtime origin;
 initial begin
  if($value$plusargs("KEEP_LOCK=%d",keep_lock))begin end
  #1000;locked=1;wait(mcu_ready===1'b1);#1000;origin=$realtime;
  fd=$fopen("fault.trace","r");if(!fd)$fatal(1,"095 fault trace missing");
  while(!$feof(fd))begin
   rc=$fscanf(fd,"%d %d %d %d %d %d\n",event_ns,kind,ss,sck,mosi,sample_value);
   if(rc==6)begin
    if(event_ns+0.002<$realtime-origin)$fatal(1,"095 fault time reversed");
    if(event_ns>$realtime-origin)#(event_ns-($realtime-origin));
    if(kind==1)begin
     faults++;if(!keep_lock)locked=0;#0.001;
     if(mcu_ready||!psram_1ce||!psram_2ce||!psram_we||!psram_oe||spi_miso!==1'bz)
      $fatal(1,"095 raw fault did not match C READY-low premise");
    end else begin
     if(sample_value>=0)begin
      compared++;if(spi_miso!==sample_value[0])$fatal(1,"095 fault-prefix MISO mismatch row%0d",rows);
     end
     SPI_SS=ss;SPI_SCK=sck;SPI_MOSI=mosi;rows++;
    end
   end else if(rc!=-1)$fatal(1,"095 malformed fault trace");
  end
  $fclose(fd);#100;
  if(faults!=1||!SPI_SS||SPI_SCK||mcu_ready||pin_writes||memory.writes||!psram_we||!psram_1ce||!psram_2ce||psram_data!==16'hzzzz)
   $fatal(1,"095 cancelled session pin ownership");
  // The MCU trace has ended after FAILED reentry attempts. A recovered FPGA
  // must contain no image, and no further MCU clocks/commands are replayed.
  locked=1;#300000;
  if(!mcu_ready||dut.boundary.loaded||dut.boundary.loaded_bytes||!psram_we||!psram_1ce||!psram_2ce)
   $fatal(1,"095 recovered FPGA reused image");
  $display("PASS095 FAULT rows=%0d compared=%0d raw_lock=1 writes=0 cancelled=1 recovered_image_empty=1",rows,compared);$finish;
 end
 initial begin #10000000;$fatal(1,"095 fault watchdog");end
endmodule
