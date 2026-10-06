// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module nes_tb;
reg clk=0; always #23.280423 clk=~clk;
reg reset_nes=1,cold_reset=1;
reg [7:0] cpumem_din=0,ppumem_din=0;
reg [4:0] joypad1_data=0,joypad2_data=0;
wire [24:0] cpumem_addr; wire [21:0] ppumem_addr;
wire cpumem_read,cpumem_write,ppumem_read,ppumem_write;
wire [7:0] cpumem_dout,ppumem_dout;
wire [5:0] color;wire [2:0] emphasis;
wire [8:0] cycle,scanline;wire [15:0] sample;
nes_probe dut(.*);
reg [7:0] prg[0:32767],chr[0:8191],ram[0:2047],nt[0:2047];
integer i,reads=0,beats=0,joy_seen=0,audio_changes=0,pixels=0,badcolors=0,pixel_errors=0,audio_unknown=0,audio_period_errors=0,last_audio_tick=-1,fd;
reg [15:0] lastsample=0;reg[8:0] prevcycle=511,prevline=511;
reg collecting=0,doneframe=0;
reg [5:0] expected_color;
integer master_ticks=0,last_cpu_tick=-1,cpu_period_errors=0,cpu_ticks=0,unknown_bus=0;
always @(posedge clk) begin
 master_ticks=master_ticks+1;
 if ($time>100000 && dut.core.cpu_ce) begin
  if(last_cpu_tick>=0 && master_ticks-last_cpu_tick!=12)begin
   if(cpu_period_errors<4)$display("CPU_PERIOD_ERROR ticks=%0d gap=%0d ppu_tick=%0d cpu_tick_count=%0d",master_ticks,master_ticks-last_cpu_tick,dut.core.ppu_tick,dut.core.cpu_tick_count);
   cpu_period_errors=cpu_period_errors+1;
  end
  last_cpu_tick=master_ticks;cpu_ticks=cpu_ticks+1;
  if($isunknown({dut.core.cpu_addr,dut.core.cpu_rnw,dut.core.internal_data_bus}))begin
   if(unknown_bus<4)$display("UNKNOWN_BUS addr=%04x rnw=%b data=%02x",dut.core.cpu_addr,dut.core.cpu_rnw,dut.core.internal_data_bus);
   unknown_bus=unknown_bus+1;
  end
 end
end
initial begin
 #1000000;
 if(cpu_ticks<1000 || cpu_period_errors!=0 || unknown_bus!=0 || pixel_errors!=0 || audio_unknown!=0 || audio_period_errors!=0)$fatal(1,"early CPU timing/known-value check failed ticks=%0d period_errors=%0d unknown=%0d",cpu_ticks,cpu_period_errors,unknown_bus);
end
initial begin
 repeat(12) begin
  #10000000;
  $display("PROGRESS time=%0t pc=%04x heartbeat=%0d joy=%0d cpu_period_errors=%0d unknown_bus=%0d pixels=%0d",$time,dut.core.cpu_addr,beats,joy_seen,cpu_period_errors,unknown_bus,pixels);
 end
end
always @(posedge clk) begin
 if(cpumem_read) begin
  reads<=reads+1;
  if(cpumem_addr<32768) cpumem_din<=prg[cpumem_addr];
  else if(cpumem_addr>=25'h380000 && cpumem_addr<25'h380800) cpumem_din<=ram[cpumem_addr[10:0]];
  else cpumem_din<=0;
 end
 if(cpumem_write && cpumem_addr>=25'h380000 && cpumem_addr<25'h380800) begin
  ram[cpumem_addr[10:0]]<=cpumem_dout;
  if(cpumem_addr[10:0]==0) beats<=beats+1;
  if(cpumem_addr[10:0]==1 && cpumem_dout==1) joy_seen<=joy_seen+1;
 end
 if(ppumem_read) begin
  if(ppumem_addr>=22'h200000 && ppumem_addr<22'h202000) ppumem_din<=chr[ppumem_addr[12:0]];
  else if(ppumem_addr>=22'h3a0000 && ppumem_addr<22'h3a0800) ppumem_din<=nt[ppumem_addr[10:0]];
  else ppumem_din<=0;
 end
 if(ppumem_write && ppumem_addr>=22'h3a0000 && ppumem_addr<22'h3a0800) nt[ppumem_addr[10:0]]<=ppumem_dout;
 if($time>60000000) begin
  if($isunknown(sample))audio_unknown<=audio_unknown+1;
  if(sample!==lastsample) begin
   audio_changes<=audio_changes+1;
   // 50% pulse at timer 253: amplitude edges every 8*(253+1) CPU cycles.
   if(last_audio_tick>=0 && master_ticks-last_audio_tick!=24384)audio_period_errors<=audio_period_errors+1;
   last_audio_tick=master_ticks;
  end
 end
 lastsample<=sample;
end
always @(negedge clk) begin
 if(cycle!=prevcycle || scanline!=prevline) begin
  if($time>80000000 && scanline==0 && cycle==2 && !collecting && !doneframe) collecting=1;
  if(collecting && scanline<240 && cycle>=2 && cycle<=257) begin
   // color_pipe[0] is registered while ClockGen increments: pixel x appears at cycle=x+2.
   // This captures all 256 source pixels, including x=255 at cycle 257.
   expected_color=((((cycle-2)&1)^scanline[0])!=0) ? 6'h0f : 6'h21;
   if(color!==expected_color)pixel_errors=pixel_errors+1;
   $fwrite(fd,"%02x\n",color);pixels=pixels+1;
   if(color!==6'h0f && color!==6'h21)badcolors=badcolors+1;
  end
  if(collecting && scanline==240)begin collecting=0;doneframe=1;end
 end
 prevcycle=cycle;prevline=scanline;
end
initial begin
 $readmemh("prg.hex",prg);$readmemh("chr.hex",chr);
 for(i=0;i<2048;i=i+1)begin ram[i]=0;nt[i]=0;end
 fd=$fopen("frame-color.hex","w");
 #20000;reset_nes=0;cold_reset=0;
 #60000000;joypad1_data=1;
 #60000000;$fclose(fd);
 // ROM sets pulse timer=$0FD: CPU/(16*254) ~= 440.4 Hz.
 // The 60.02ms observation window must contain 52..54 amplitude edges, phase dependent.
 $display("RESULT reads=%0d heartbeat=%0d joy=%0d audio_changes=%0d pixels=%0d badcolors=%0d cpu_ticks=%0d cpu_period_errors=%0d unknown_bus=%0d pixel_errors=%0d audio_unknown=%0d audio_period_errors=%0d",reads,beats,joy_seen,audio_changes,pixels,badcolors,cpu_ticks,cpu_period_errors,unknown_bus,pixel_errors,audio_unknown,audio_period_errors);
 if(beats<100 || joy_seen<100 || (audio_changes<52 || audio_changes>54) || pixels!=61440 || badcolors!=0 || cpu_period_errors!=0 || unknown_bus!=0 || pixel_errors!=0 || audio_unknown!=0 || audio_period_errors!=0)$fatal(1,"diagnostic failed");
 $display("PASS NES DIAGNOSTIC");$finish;
end
endmodule
