// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module screen141_tb #(parameter LEGACY=0, parameter real ACK=16.0, parameter CAPTURE=1);
 defparam dut.core.dut.core.LEGACY_DEADLINE141=LEGACY;
 defparam dut.core.loader_boot.boot.reader.ACK_DELAY=ACK;
 defparam dut.core.loader_boot.boot.reader.CAPTURE=CAPTURE;
 reg CLKIN=0,SNES_SYSCLK=0,SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 always #62.5 CLKIN=~CLKIN;
 real half_ns=23.28,phase_ns=3.5;
 initial begin void'($value$plusargs("HALF=%f",half_ns));void'($value$plusargs("PHASE=%f",phase_ns));#(phase_ns);forever #(half_ns) SNES_SYSCLK=~SNES_SYSCLK;end
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
 reg injected=0;reg [63:0] expected_context,received_context;
 integer starts=0,ends=0,bytes_read=0,pixels=0,checks=0,fd,fp;
 reg collecting=0;reg [8:0] prevcycle=511,prevline=511;
 reg [7:0] rx;
 task automatic ck(input bit ok,input string why);
  checks++;if(!ok)$fatal(1,"SCREEN137 %s time=%0f",why,$realtime);
 endtask
 task automatic byte_io(input [7:0] tx,output [7:0] r);
  for(integer b=7;b>=0;b--)begin SPI_MOSI=tx[b];#2000;SPI_SCK=1;#1;r[b]=SPI_MISO;#1999;SPI_SCK=0;end
 endtask
 function automatic [7:0] crc_byte(input [7:0] old,value);
  reg [7:0] c;begin c=old^value;for(integer i=0;i<8;i++)c=c[7]?(c<<1)^8'h07:c<<1;crc_byte=c;end
 endfunction
 task automatic command(input [7:0] op,input [23:0] offset);
  reg [7:0] b[0:7],r,c;
  b[0]=op;b[1]=offset[23:16];b[2]=offset[15:8];b[3]=offset[7:0];b[4]=0;b[5]=255;c=0;
  for(integer i=0;i<6;i++)c=crc_byte(c,b[i]);b[6]=c;b[7]=8'ha5;
  SPI_SS=0;#2000;for(integer i=0;i<8;i++)begin
   byte_io(b[i],r);if(op==8'h65&&i==1)ck(r==8'h5d,"loader5B");
  end
  #2000;SPI_SS=1;#3000;
 endtask
 task automatic context_read;
  reg [7:0] r;reg [63:0] value;value=0;
  SPI_SS=0;#2000;byte_io(8'h71,r);byte_io(0,r);ck(r==8'hd8,"page71 id");byte_io(0,r);ck(r==1,"page71 valid");
  for(integer i=0;i<5;i++)begin byte_io(0,r);value=(value<<8)|r;end
  SPI_SS=1;#3000;SPI_SS=0;#2000;byte_io(8'h72,r);byte_io(0,r);ck(r==8'hd8,"page72 id");byte_io(0,r);ck(r==1,"page72 valid");
  for(integer i=0;i<3;i++)begin byte_io(0,r);value=(value<<8)|r;end
  byte_io(0,r);ck(r==1,"first CPU deadline");byte_io(0,r);ck(r==1,"context schema");SPI_SS=1;#3000;
  received_context=value;ck(value==expected_context,"same-edge context retained, two coherent pages");
 endtask
 task automatic wr(input [23:0] a,input [7:0] value);
  SNES_ADDR_IN=a;host_data=value;SNES_ROMSEL_IN=1;#20;SNES_WRITE_IN=0;#180;
  ck(!SNES_DATABUS_DIR,"write cannot drive host");SNES_WRITE_IN=1;#20;SNES_ADDR_IN=24'h123456;#100;
 endtask
 task automatic rd(input [23:0] a,input bit cart,output [7:0] value);
  SNES_ADDR_IN=a;SNES_ROMSEL_IN=!cart;#20;SNES_READ_IN=0;#160;
  ck(!SNES_DATABUS_OE&&SNES_DATABUS_DIR&&!$isunknown(SNES_DATA),"read valid");value=SNES_DATA;
  #60;SNES_READ_IN=1;SNES_ROMSEL_IN=1;SNES_ADDR_IN=24'habcd00;
  #0.001;ck(SNES_DATABUS_OE&&!SNES_DATABUS_DIR&&SNES_DATA===8'hzz,"raw release");#100;
 endtask
 task automatic consume(input integer seqnum);
  integer polls;reg [7:0] value;
  wr(24'h6002,1);wr(24'h6003,0);wr(24'h6004,seqnum);wr(24'h6005,0);wr(24'h6000,1);
  polls=0;while(!dut.core.ready && !dut.core.fault && polls<50000)begin
   #100;polls++;if(!dut.core.busy&&!dut.core.ready&&!dut.core.fault)wr(24'h6000,1);
  end
  ck(dut.core.ready&&!dut.core.fault,"acquire");
  rd(24'h6006,0,value);ck(value==8'hd8,"length low");rd(24'h6007,0,value);ck(value==7,"length high");
  for(integer i=0;i<2008;i++)begin rd(24'h408000+i,1,value);$fwrite(fd,"%02x\n",value);bytes_read++;end
  rd(24'h6008,0,value);ck(value==8'hd8,"read low");rd(24'h6009,0,value);ck(value==7,"read high");
  wr(24'h6000,2);polls=0;while(dut.core.busy&&polls<50000)begin #100;polls++;end
  ck(!dut.core.busy&&!dut.core.fault&&!dut.core.frontend_error,"commit");
 endtask
 integer tracefile,targethits=0;
 initial tracefile=$fopen("boundary-trace.txt","w");
 always @(posedge SNES_SYSCLK) if(!dut.core_reset)begin
  if((dut.observer.samples>=122980 && dut.observer.samples<=123080) || dut.fault_trigger)
   $fwrite(tracefile,"t=%0f samples=%0d cpu=%h div=%0d cs=%b cv=%b ce=%b cr=%b ppu=%h ps=%b pe=%b pr=%b busy=%b pp=%b pending=%h age=%0d req=%b reqaddr=%h rsp=%b ready=%b readerstate=%0d ack=%b sync=%b tag=%h cached=%b\n",$realtime,dut.observer.samples,dut.core.cpumem_addr,dut.core.dut.core.div_cpu,dut.core.rom_cpu_sample,dut.core.rom_cpu_valid,dut.core.rom_cpu_address_valid,dut.core.cpumem_read,dut.core.ppumem_addr,dut.core.tap_ce&&dut.core.ppumem_read,dut.core.rom_ppu_address_valid,dut.core.ppumem_read,dut.core.rom_service.busy,dut.core.rom_service.pending_ppu,dut.core.rom_service.pending_address,dut.core.rom_service.age,dut.core.rom_request,dut.core.rom_address,dut.core.rom_response,dut.core.rom_ready,dut.core.loader_boot.boot.reader.state,dut.core.loader_boot.boot.reader.ack_toggle,dut.core.loader_boot.boot.reader.ack_sync,dut.core.rom_service.cpu_tag,dut.core.rom_service.cpu_cached);
  if(dut.core.rom_cpu_sample && dut.core.cpumem_addr==25'he184)begin
   targethits++;if(targethits<4)$display("TARGET141 sample=%0d age=%0d ready=%b response=%b pending=%h owner=%b time=%0f",dut.observer.samples,dut.core.rom_service.age,dut.core.rom_ready,dut.core.rom_response,dut.core.rom_service.pending_address,dut.core.rom_service.pending_ppu,$realtime);
  end
  if(dut.fault_trigger)begin
   $display("FIRST141 sample=%0d context=%h time=%0f",dut.observer.samples,dut.fault_context,$realtime);$fclose(tracefile);
  end
 end
 integer actual_cpu141=0,open_bus141=0;
 reg [7:0] expected141;
 always @(posedge SNES_SYSCLK) if(!dut.core_reset)begin
  if(dut.core.dut.core.mr_int && dut.core.dut.core.prg_addr[15] && dut.core.dut.core.prg_allow && (dut.core.dut.core.cpu_ce || dut.core.dut.core.div_cpu==11))begin
   expected141=ram.prg[dut.core.cpumem_addr[15:0]];
   ck(dut.core.cpumem_din===expected141,"actual CPU/DMA or final open-bus input byte");
   if(dut.core.dut.core.cpu_ce)actual_cpu141++;else open_bus141++;
  end
 end
 always @(posedge SNES_SYSCLK)if(!dut.core_reset)begin
  if(dut.core.frame_start)begin
   starts++;collecting=1;fp=$fopen($sformatf("frame-%0d.hex",starts),"w");
   ck(dut.core.frame_ready&&dut.core.supported_mode,"capture initialized and idle");
  end
  if(dut.core.frame_end)begin ends++;collecting=0;$fclose(fp);end
  if(dut.core.encoder_fault||dut.core.producer_fault||dut.core.tap_fault||dut.core.fault||(dut.rom_fault&&!injected))
   $fatal(1,"SCREEN137 fault tap=%h encoder=%h producer=%h bus=%h rom=%h time=%0f",dut.core.tap_error,dut.core.encoder_error,dut.core.producer_error,dut.core.bus_error,dut.rom_error,$realtime);
 end
 always @(negedge SNES_SYSCLK)begin
  if(collecting&&(dut.core.cycle!=prevcycle||dut.core.scanline!=prevline)&&dut.core.scanline<240&&dut.core.cycle>=2&&dut.core.cycle<=257)begin
   ck(!$isunknown(dut.core.color)&&dut.core.emphasis==0,"pixel defined");$fwrite(fp,"%02x\n",dut.core.color);pixels++;
  end
  prevcycle=dut.core.cycle;prevline=dut.core.scanline;
 end
 initial begin
  fd=$fopen("packets.hex","w");wait(MCU_RDY);#1000;
  ck(SNES_DATABUS_OE&&SNES_DATA===8'hzz,"before RUN isolation");command(8'h65,0);
  begin reg [7:0] r;SPI_SS=0;#2000;byte_io(8'h70,r);byte_io(0,r);ck(r==8'hd8,"observerD8");
   for(integer i=0;i<6;i++)byte_io(0,r);SPI_SS=1;#3000;end
  command(8'h60,0);
  $readmemh("prg.hex",ram.prg);$readmemh("chr.hex",ram.chr,0,16383);
  @(negedge dut.core.mem_clk);dut.core.loader_boot.boot.loader.loaded_bytes=81920;
  command(8'h62,81920);@(negedge dut.core.mem_clk);dut.core.loader_boot.control.verified=1;
  command(8'h63,81920);wait(!dut.core_reset);
  rd(24'h008000,1,rx);ck(rx==8'h78,"consumer boot opcode");
  rd(24'h00fffc,1,rx);ck(rx==0,"reset vector low");rd(24'h00fffd,1,rx);ck(rx==8'h80,"reset vector high");
  rd(24'h600b,0,rx);ck(rx==1,"cold epoch low");rd(24'h600c,0,rx);ck(rx==0,"cold epoch high");
  #65000000;
  $display("FINAL141 samples=%0d error=%d",dut.observer.samples,dut.rom_error);
  ck(!dut.rom_fault,"targeted normal run");
  command(8'h64,81920);ck(dut.core_reset&&!dut.core.run_enable,"physical SPI STOP");
  SNES_ADDR_IN=24'h008000;SNES_ROMSEL_IN=0;SNES_READ_IN=0;#200;
  ck(SNES_DATABUS_OE&&SNES_DATA===8'hzz,"STOP cannot expose program or payload");
  ck(ram.writes==0,"seeded fixture; no fullwrites repeated");
  $fclose(fd);$display("PASS141 checks=%0d actualCPU=%0d openbus=%0d",checks,actual_cpu141,open_bus141);$finish;
 end
 initial begin repeat(25)begin #10000000;$display("PROGRESS137 t=%0f starts=%0d ends=%0d bytes=%0d",$realtime,starts,ends,bytes_read);end $fatal(1,"SCREEN137 watchdog");end
endmodule
