// SPDX-License-Identifier: MIT
// Actual joint131 RTL, modeled PLL and pin RAM. Only image/verified fixture seeded.
`timescale 1ns/1ps
module run133_tb;
 reg ext_clk=0,CLKIN=0,ext_reset=1,ext_chr32=0;
 reg source_running=1;integer phase=0;
 initial begin if($value$plusargs("PHASE_PS=%d",phase))begin end
  #(phase*0.001);forever #22.727 if(source_running)ext_clk=~ext_clk;end
 always #62.5 CLKIN=~CLKIN;
 reg ext_SPI_SS=1,ext_SPI_SCK=0,ext_SPI_MOSI=0;
 wire out_spi_fault,out_run_enable,out_loaded;
 wire [21:0] out_psram_address;
 wire out_psram_1ce,out_psram_2ce,out_psram_oe,out_psram_we,out_psram_bhe,out_psram_ble;
 tri [15:0] ext_psram_data;
 nes_live_joint dut(.ext_clk(ext_clk),.CLKIN(CLKIN),.ext_reset(ext_reset),.ext_chr32(ext_chr32),
  .ext_reset_epoch(16'd1),.ext_arm(1'b0),.ext_immutable_chr(1'b1),
  .ext_snes_addr(24'd0),.ext_read_n(1'b1),.ext_write_n(1'b1),.ext_romsel_n(1'b1),.ext_snes_data_in(8'd0),
  .ext_joypad1(5'd0),.ext_joypad2(5'd0),
  .ext_SPI_SS(ext_SPI_SS),.ext_SPI_SCK(ext_SPI_SCK),.ext_SPI_MOSI(ext_SPI_MOSI),
  .out_spi_fault(out_spi_fault),.out_run_enable(out_run_enable),.out_loaded(out_loaded),
  .ext_psram_data(ext_psram_data),.out_psram_address(out_psram_address),
  .out_psram_1ce(out_psram_1ce),.out_psram_2ce(out_psram_2ce),.out_psram_oe(out_psram_oe),
  .out_psram_we(out_psram_we),.out_psram_bhe(out_psram_bhe),.out_psram_ble(out_psram_ble));
 rom_boot_model ram(.reset(ext_reset),.psram_address(out_psram_address),.psram_data(ext_psram_data),
  .psram_1ce(out_psram_1ce),.psram_2ce(out_psram_2ce),.psram_oe(out_psram_oe),
  .psram_we(out_psram_we),.psram_bhe(out_psram_bhe),.psram_ble(out_psram_ble));
 integer checks=0,requests=0,responses=0,launches=0,stops=0,chr_changes=0;
 integer releases=0,scrub_ticks=0,expected_mode=0,total=0,trace;
 realtime chr_time=0,run_time=0,min_chr_age=1e9,min_run_age=1e9;
 reg monitoring=0;reg [2:0] loop_bytes=0;reg reset_vector_seen=0;
 task automatic ck(input bit ok,input string why);
  checks++;if(!ok)$fatal(1,"RUN133 %s checks=%0d time=%0f",why,checks,$realtime);
 endtask
 function automatic [7:0] crc_byte(input [7:0] previous,value);
  reg [7:0] c;begin c=previous^value;
   for(integer i=0;i<8;i++)c=c[7]?(c<<1)^8'h07:c<<1;crc_byte=c;end
 endfunction
 task automatic command(input [7:0] op,input [23:0] offset,input [7:0] arg,input bit bad=0);
  reg [7:0] b[0:7];reg [7:0] crc;
  b[0]=op;b[1]=offset[23:16];b[2]=offset[15:8];b[3]=offset[7:0];b[4]=arg;b[5]=~arg;crc=0;
  for(integer i=0;i<6;i++)crc=crc_byte(crc,b[i]);b[6]=bad?(crc^8'h01):crc;b[7]=8'ha5;
  ext_SPI_SS=0;#120;
  for(integer i=0;i<8;i++)for(integer j=7;j>=0;j--)begin
   ext_SPI_MOSI=b[i][j];#60;ext_SPI_SCK=1;#60;ext_SPI_SCK=0;
  end
  #120;ext_SPI_SS=1;#180;
 endtask
 // Contract observations are on actual top nets, not a duplicated reset model.
 always @(posedge dut.run_enable)if(monitoring)begin run_time=$realtime;launches++;end
 always @(dut.chr_32k)if(monitoring)begin
  chr_time=$realtime;chr_changes++;
  #0.001;ck(dut.reset && dut.raw_stop,"CHR changed while consumer active");
 end
 always @(posedge ext_clk)if(monitoring)begin
  if(dut.reset_request)scrub_ticks=0;
  else if(!dut.memory_ready)scrub_ticks++;
  if(!dut.reset)begin
   ck(dut.memory_ready && dut.run_enable && !dut.common_reset,"consumer released before initialization");
   ck(dut.chr_32k==expected_mode,"consumer CHR mode");
  end
  if(dut.rom_request)begin
   ck(!dut.reset && dut.memory_ready && dut.run_enable,"request before RUN release");
   ck(!dut.loader_boot.boot.reader.sr && dut.rom_ready,"request while source held");
   ck($realtime-chr_time>45.454,"CHR setup before request");requests++;
  end
  if(dut.rom_response)begin
   ck(!$isunknown(dut.rom_data),"unknown CPU/PPU response");
   ck(dut.rom_data==ram.value({2'd0,dut.rom_response_address}),"CPU/PPU response byte mismatch");responses++;
   if(dut.rom_response_address<3)loop_bytes[dut.rom_response_address]=1;
   if(dut.rom_response_address==22'hfffc)reset_vector_seen=1;
   $fdisplay(trace,"RESPONSE %0f run=%0d address=%06h data=%02h",$realtime,launches,dut.rom_response_address,dut.rom_data);
  end
 end
 always @(negedge dut.reset)if(monitoring)begin
  #0.001;ck(dut.memory_ready && scrub_ticks>=8192,"core release skipped RAM scrub");
  ck($realtime-chr_time>45.454,"CHR setup before core release");
  if($realtime-chr_time<min_chr_age)min_chr_age=$realtime-chr_time;
  if($realtime-run_time<min_run_age)min_run_age=$realtime-run_time;
  releases++;$fdisplay(trace,"RELEASE %0f mode=%0d scrub=%0d run_age=%0f chr_age=%0f",$realtime,expected_mode,scrub_ticks,$realtime-run_time,$realtime-chr_time);
 end
 always @(posedge dut.common_reset)if(monitoring)begin
  #0.001;ck(dut.reset,"common reset did not assert core reset");
  ck(!dut.rom_request,"request after common reset");
 end
 task automatic fresh;
  monitoring=0;ext_reset=1;source_running=1;dut.pll.memory_running=1;
  ext_SPI_SS=1;ext_SPI_SCK=0;ext_SPI_MOSI=0;#250;ext_reset=0;
  wait(dut.external_memory_ready);repeat(8)@(negedge dut.mem_clk);
  ck(dut.reset && !dut.run_enable,"initial held state");
  chr_time=$realtime;monitoring=1;
 endtask
 task automatic image(input bit mode);
  expected_mode=mode;total=mode?98304:81920;
  command(8'h60,0,{7'd0,mode});ck(dut.loader_boot.boot.loader.state==1,"BEGIN actual decoder/loader");
  // Writes/CHECK were verified131. Seed only their completion state and image.
  for(integer a=0;a<65536;a++)ram.prg[a]=8'hea;
  for(integer a=0;a<32768;a++)ram.chr[a]=a[7:0];
  // Synthetic CPU program: JMP $8000, all vectors $8000. No game ROM used.
  ram.prg[0]=8'h4c;ram.prg[1]=0;ram.prg[2]=8'h80;
  for(integer a=65530;a<65536;a++)ram.prg[a]=a[0]?8'h80:8'h00;
  @(negedge dut.mem_clk);dut.loader_boot.boot.loader.loaded_bytes=total;
  command(8'h62,total,0);ck(out_loaded && !out_run_enable,"END actual decoder/loader");
 endtask
 task automatic start_run;
  integer before_response;
  // Explicit fixture boundary: bypass full CHECK, but START command is real SPI.
  @(negedge dut.mem_clk);dut.loader_boot.control.verified=1;
  before_response=responses;command(8'h63,total,0);
  ck(out_run_enable && !out_spi_fault,"START actual decoder/loader");
  wait(!dut.reset);wait(responses>=before_response+12);
  ck(!dut.rom_fault && !dut.boot_fault && !out_spi_fault,"normal RUN fault");
 endtask
 task automatic cancelled(input string cause);
  #0.001;ck(dut.reset && !dut.rom_request,"cancel core/request");
  ck(dut.loader_boot.boot.reader.sr && dut.loader_boot.boot.reader.mr,"cancel both reader domains");
  ck(out_psram_1ce && out_psram_2ce && out_psram_oe,"cancel physical read pins");
  ck(!dut.loader_boot.boot.reader.owner_valid,"cancel captured owner");
  stops++;$fdisplay(trace,"CANCEL %0f %s responses=%0d",$realtime,cause,responses);
 endtask
 initial begin
  trace=$fopen("lifecycle133.tsv","w");#1;
  for(integer mode=0;mode<2;mode++)begin
   fresh();image(mode!=0);start_run();
   // Unused external geometry input must never control the accepted geometry.
   ext_chr32=~expected_mode;repeat(6)@(negedge ext_clk);ck(dut.chr_32k==expected_mode,"external CHR isolation");
   command(8'h64,total,0);ck(!out_run_enable && out_loaded,"STOP retains image READY");cancelled("STOP");
   repeat(8)@(negedge ext_clk);ck(dut.reset && !dut.rom_response,"no stale response after STOP");
   start_run(); // Same image, new scrub and reset-release sequence.
   command(8'h64,total,0);cancelled("STOP_BEFORE_RELOAD");
   image(mode==0);start_run(); // Change accepted geometry while consumers held.
   command(8'h65,0,0,1);ck(out_spi_fault && !out_run_enable,"bad CRC blocks RUN");cancelled("SPI_CRC");
   repeat(8)@(negedge ext_clk);ck(dut.reset,"sticky SPI fault");
   fresh();image(mode!=0);start_run();
   wait(dut.loader_boot.boot.reader.reading_active);#0.75;ext_reset=1;cancelled("RAW_RESET");
  end
  fresh();image(1);start_run();
  wait(dut.loader_boot.boot.reader.reading_active);#0.75;source_running=0;
  #10000;ck(dut.guard_fault && !out_run_enable,"source clock loss");cancelled("SOURCE_CLOCK_STOP");
  source_running=1;#3000;ck(dut.guard_fault && dut.reset,"source clock return cannot rearm");
  fresh();image(0);start_run();
  wait(dut.loader_boot.boot.reader.reading_active);#0.75;dut.pll.memory_running=0;
  #10000;ck(dut.guard_fault && !out_run_enable,"memory clock loss");cancelled("MEMORY_CLOCK_STOP");
  dut.pll.memory_running=1;#3000;ck(dut.guard_fault && dut.reset,"memory clock return cannot rearm");
  fresh();image(0);command(8'h63,total,0);
  ck(out_spi_fault && !out_run_enable && dut.loader_boot.control.error_code==8,"unverified START rejected");cancelled("UNVERIFIED_START");
  ck(launches==10 && releases==10 && stops==11,"coverage counters");ck(ram.writes==0,"no unchanged full writes repeated");
  ck(loop_bytes==7 && reset_vector_seen,"actual CPU vector and JMP operands observed");
  $display("PASS133 joint launches=%0d releases=%0d cancels=%0d requests=%0d responses=%0d chr_changes=%0d min_run_age=%0f min_chr_age=%0f phase_ps=%0d checks=%0d",launches,releases,stops,requests,responses,chr_changes,min_run_age,min_chr_age,phase,checks);
  $fclose(trace);$finish;
 end
 initial begin #20000000;$fatal(1,"RUN133 watchdog");end
endmodule
