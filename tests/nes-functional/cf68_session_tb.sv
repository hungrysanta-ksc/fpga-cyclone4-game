// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module cf68_session_tb;
 reg board8=0,locked=0,SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 always #62.5 board8=~board8;
 wire [15:0] psram_data;wire [7:0] snes_bus,ram_bus;
 wire [21:0] psram_address;wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;
 wire spi_miso,mcu_ready,rom_zz,ram_oe,ram_we,snes_irq,bus_oe,bus_dir;
 fxpak_nes_diagnostic_top dut(.CLKIN(board8),.SNES_CIC_CLK(1'b0),
 .SNES_ADDR_IN(24'd0),.SNES_READ_IN(1'b1),.SNES_WRITE_IN(1'b1),.SNES_ROMSEL_IN(1'b1),
 .SNES_CPU_CLK_IN(1'b0),.SNES_REFRESH(1'b0),.SNES_SYSCLK(1'b0),.SNES_PA_IN(8'd0),.SNES_PARD_IN(1'b1),.SNES_PAWR_IN(1'b1),
 .SNES_DATA(snes_bus),.SNES_IRQ(snes_irq),.SNES_DATABUS_OE(bus_oe),.SNES_DATABUS_DIR(bus_dir),
 .SPI_MOSI(SPI_MOSI),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MISO(spi_miso),.MCU_RDY(mcu_ready),
 .ROM_ADDR(psram_address),.ROM_1CE(psram_1ce),.ROM_2CE(psram_2ce),.ROM_ZZ(rom_zz),
 .ROM_OE(psram_oe),.ROM_WE(psram_we),.ROM_BHE(psram_bhe),.ROM_BLE(psram_ble),.ROM_DATA(psram_data),
 .RAM_ADDR(),.RAM_OE(ram_oe),.RAM_WE(ram_we),.RAM_DATA(ram_bus),.DAC_MCLK(),.DAC_LRCK(),.DAC_SDOUT());
 rom_boot_model memory(.reset(!locked),.*);
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
  if(dut.boundary.run_active||dut.boundary.nes_run_enable)$fatal(1,"070 unexpected RUN");
 always @(posedge psram_we)if(locked&&(!psram_1ce ^ !psram_2ce))begin
  if({psram_address,psram_1ce,1'b0}!==((pin_writes<65536?pin_writes:22'h200000+pin_writes-65536)&22'h3ffffe)||
     psram_bhe!==pin_writes[0]||psram_ble!==!pin_writes[0])$fatal(1,"070 physical write address/lane at%0d",pin_writes);
  pin_writes++;
 end
 always @(negedge psram_oe)if(locked)begin
  if(!psram_we||!(!psram_1ce ^ !psram_2ce))$fatal(1,"070 read ownership");
  if({psram_address,psram_1ce,1'b0}!==((reads<65536?reads:22'h200000+reads-65536)&22'h3ffffe))
   $fatal(1,"070 physical read address at%0d",reads);
  // The existing reader enables the complete16-bit word, then chooses the
  // requested byte internally. Byte-write strobes do not apply to reads.
  if(psram_bhe!==1'b0||psram_ble!==1'b0)$fatal(1,"070 physical read word enables at%0d",reads);
  reads++;
 end
 reg [7:0] expected[0:98303];
 reg [63:0] tx,rx;longint unsigned start_ns,end_ns;
 integer fd,rc,bits;
 realtime origin;
 task automatic check_written;
  if(memory.writes!=pin_writes||pin_writes!=data_frames)$fatal(1,"070 prefix write count");
  for(integer a=0;a<pin_writes;a++)
   if((a<65536?memory.prg[a]:memory.chr[a-65536])!==expected[a])$fatal(1,"070 physical RAM byte%0d",a);
 endtask
 task automatic frame;
  if(start_ns<($realtime-origin))$fatal(1,"070 non-monotonic captured time");
  #(start_ns-($realtime-origin));SPI_SCK=0;SPI_SS=0;#2000;
  for(integer i=0;i<bits;i++)begin
   SPI_MOSI=tx[63-i];#2000;SPI_SCK=1;#2000;
   if(i>=8)begin
    if(park_legacy&&frames>=3&&!dut.boundary.loader_selected)$fatal(1,"070 parked legacy reply selected");
    checked++;
    if(spi_miso!==rx[63-i])$fatal(1,"070 MCU sample mismatch frame%0d op%h bit%0d got%b expected%b",frames,tx[63:56],i,spi_miso,rx[63-i]);
   end
   SPI_SCK=0;if(i%8==7)#2000;
  end
  #2000;
  if(frames==0&&(tx[63:56]!=8'hcf||rx[55:48]!=8'h68))$fatal(1,"070 CF68 capture missing");
  if($realtime-origin!=end_ns)$fatal(1,"070 C edge timing mismatch");
  SPI_SS=1;frames++;
  // After CF/F0/F1, every captured command must use the8MHz loader decoder.
  // The legacy H1 domain is unused and reset-held for this load-only session.
  if(park_legacy&&frames==3)begin
   if(tx[63:56]!=8'hf1||!dut.boundary.link.reset||dut.boundary.run_active)
    $fatal(1,"070 legacy park precondition");
   dut.pll.enable=0;
  end
  #2000;
  case(tx[63:56])
   8'h61:data_frames++;
   8'h62:begin ends++;if(!dut.boundary.loaded||memory.writes!=total)$fatal(1,"070 END state");end
   8'h68:acks++;
   8'h69:begin finishes++;if(!dut.boundary.loader.control.verified||reads!=total||acks!=total)$fatal(1,"070 FINISH state");end
   8'h64:begin stops++;if(dut.boundary.loaded||dut.boundary.loaded_bytes||dut.boundary.loader.control.verified)$fatal(1,"070 STOP state");end
   8'h63,8'he8:$fatal(1,"070 C attempted START");
   default:;
  endcase
  if(dut.boundary.spi_fault||dut.boundary.boot_fault)$fatal(1,"070 protocol or loader fault");
  if(frames==64)begin
   check_written();$display("SESSION BOUNDARY frames=64 writes=%0d reads=%0d checked=%0d",memory.writes,reads,checked);
  end
  if(frames%40960==0||frames==1024)$display("SESSION PROGRESS frames=%0d writes=%0d reads=%0d",frames,memory.writes,reads);
 endtask
 initial begin
  if($value$plusargs("TOTAL=%d",total))begin end
  if($value$plusargs("LIMIT_FRAMES=%d",limit_frames))begin end
  if($value$plusargs("PARK_LEGACY=%d",park_legacy))begin end
  if(total!=81920&&total!=98304)$fatal(1,"070 geometry");
  $readmemh("expected.hex",expected,0,total-1);
  #1000;locked=1;#1000;
  if(mcu_ready||!psram_1ce||!psram_2ce||!psram_we||!psram_oe)
   $fatal(1,"070 early startup pins");
  // Model the MCU READY boundary before captured GPIO. Do not alter captured
  // within-frame times or the continuously free-running8MHz memory/SPI clock.
  #180000;
  if(mcu_ready||!psram_1ce||!psram_2ce||!psram_we||!psram_oe)
   $fatal(1,"070 early startup access");
  wait(mcu_ready===1'b1);
  if($realtime<201000||$realtime>252000)$fatal(1,"070 startup READY interval");
  $display("SESSION STARTUP ready_ns=%0t clock8_free_running=1",$realtime);
  #1000;
  if(!dut.boundary.link.reset||dut.boundary.generation!=0)$fatal(1,"070 reset-held clock mask precondition");
  if(mask_link)link_clocks=0;#1000;origin=$realtime;
  fd=$fopen("session.trace","r");if(!fd)$fatal(1,"070 trace missing");
  while(!$feof(fd))begin
   rc=$fscanf(fd,"%d %d %d %h %h\n",start_ns,end_ns,bits,tx,rx);
   if(rc==5)begin
    if(bits!=16&&bits!=64)$fatal(1,"070 malformed captured frame");
    if(park_legacy&&frames>=3&&tx[63:60]!=4'h6)$fatal(1,"070 parked legacy domain used");
    frame();
    if(limit_frames!=0&&frames==limit_frames)begin
     check_written();
     $display("PASS SESSION PREFIX frames=%0d writes=%0d reads=%0d checked=%0d mask_link=%0d park_legacy=%0d",frames,memory.writes,reads,checked,mask_link,park_legacy);$finish;
    end
   end else if(rc!=-1)$fatal(1,"070 malformed captured row");
  end
  $fclose(fd);
  if(frames!=total*5+16||data_frames!=total||memory.writes!=total||pin_writes!=total||reads!=total||acks!=total||ends!=1||finishes!=1||stops!=1)
   $fatal(1,"070 incomplete full session");
  if(!psram_1ce||!psram_2ce||!psram_we||!psram_oe||psram_data!==16'hzzzz||
     !mcu_ready||!rom_zz||!ram_oe||!ram_we||ram_bus!==8'hzz||snes_bus!==8'hzz||snes_irq||!bus_oe)
   $fatal(1,"070 final peripheral ownership");
  check_written();
  $display("PASS SESSION FULL bytes=%0d frames=%0d writes=%0d reads=%0d ACK=%0d checked=%0d FINISH=%0d STOP=%0d no_RUN=1 mask_link=%0d park_legacy=%0d",total,frames,memory.writes,reads,acks,checked,finishes,stops,mask_link,park_legacy);$finish;
 end
 initial begin #252000;if(!mcu_ready)$fatal(1,"070 startup READY timeout");end
 initial begin #150000000000.0;$fatal(1,"070 full session watchdog");end
endmodule
