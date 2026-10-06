// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module mmc3_tb;
reg clk=0;always #5 clk=~clk;
reg ce=0,m2_inv=0,enable=0,paused=0;
reg [31:0] flags=4;
reg [15:0] prg_ain=0;reg prg_read=1,prg_write=0;reg [7:0] prg_din=0;
reg [13:0] chr_ain=0,chr_ain_o=0;reg chr_read=1;
wire [21:0] prg_aout_b,chr_aout_b;wire [7:0] prg_dout_b;
wire prg_allow_b,chr_allow_b,vram_a10_b,vram_ce_b,irq_b;
wire [15:0] audio_b,flags_out_b;wire [63:0] SaveStateBus_Dout;
MMC3 dut(.*, .audio_in(16'd0),.SaveStateBus_Din(64'd0),.SaveStateBus_Adr(10'd0),.SaveStateBus_wren(1'b0),.SaveStateBus_rst(1'b0),.SaveStateBus_load(1'b0));
integer fd,phase=0,ticks=0,checks=0,errors=0,mode,value,slot,off,r,testphase;
// One CPU period is 12 master ticks. CPU-write CE and falling-M2 sample are distinct.
always @(negedge clk)begin
 ce=(phase==5);m2_inv=(phase==11);phase=(phase+1)%12;
end
always @(posedge clk)ticks=ticks+1;
task tick;
 begin @(posedge clk);#1;end
endtask
task wr(input [15:0] a,input [7:0] d);
 begin
  prg_ain=a;prg_din=d;prg_write=1;prg_read=0;
  tick();while(!ce)tick();
  $fwrite(fd,"W %0d %0d %0d\n",ticks,a,d);
  prg_write=0;prg_read=1;
 end
endtask
task bank(input integer regno,input integer data,input integer ctrl);
 begin wr(16'h8000,ctrl|regno);wr(16'h8001,data);end
endtask
task pcheck(input integer a,input integer writing);
 begin prg_ain=a;prg_write=writing;prg_read=!writing;#1;
  $fwrite(fd,"P %0d %0d %0d %0d %0d\n",ticks,a,writing,prg_aout_b,prg_allow_b);checks=checks+1;prg_write=0;prg_read=1;
 end
endtask
task ccheck(input integer a);
 begin chr_ain=a;#1;$fwrite(fd,"C %0d %0d %0d %0d %0d %0d\n",ticks,a,chr_aout_b,chr_allow_b,vram_a10_b,vram_ce_b);checks=checks+1;end
endtask
task irqcheck(input string tag,input integer expected);
 begin
  #1;$fwrite(fd,"I %0d %s %0d %0d %0d\n",ticks,tag,irq_b,expected,dut.counter);checks=checks+1;
  if(irq_b!==expected[0])begin errors=errors+1;$display("IRQ_ERROR %s phase=%0d got=%b expected=%0d counter=%0d",tag,testphase,irq_b,expected,dut.counter);end
 end
endtask
task low_samples(input integer n);
 integer k;
 begin chr_ain_o=0;tick();k=m2_inv?1:0;while(k<n)begin tick();if(m2_inv)k=k+1;end repeat(testphase)tick();end
endtask
task rise;
 begin chr_ain_o=14'h1000;tick();end
endtask
task pulse;
 begin low_samples(3);rise();end
endtask
task reset_mapper;
 begin enable=0;chr_ain_o=0;prg_write=0;repeat(2)tick();enable=1;tick();end
endtask
initial begin
 fd=$fopen("mapper-trace.txt","w");reset_mapper();
 for(mode=0;mode<2;mode=mode+1)begin
  for(value=0;value<256;value=value+1)begin
   bank(6,value,mode*64);bank(7,255-value,mode*64);
   for(slot=0;slot<4;slot=slot+1)begin pcheck(16'h8000+slot*8192,0);pcheck(16'h9fff+slot*8192,0);end
  end
 end
 for(mode=0;mode<2;mode=mode+1)begin
  for(value=0;value<256;value=value+1)begin
   for(r=0;r<6;r=r+1)bank(r,(value+r*37)&255,mode*128);
   for(slot=0;slot<8;slot=slot+1)begin ccheck(slot*1024);ccheck(slot*1024+1023);end
  end
 end
 for(value=0;value<4;value=value+1)begin
  wr(16'ha001,value*64);
  pcheck(16'h6000,0);pcheck(16'h7fff,0);pcheck(16'h6000,1);pcheck(16'h7fff,1);
 end
 for(value=0;value<2;value=value+1)begin
  wr(16'ha000,value);for(slot=0;slot<4;slot=slot+1)ccheck(16'h2000+slot*1024);
 end
 // Standard Mapper4 only: repeat IRQ protocol at all 12 initial master phases.
 for(testphase=0;testphase<12;testphase=testphase+1)begin
  reset_mapper();wr(16'hc000,1);wr(16'hc001,0);wr(16'he001,0);
  while(phase!=testphase)tick();
  pulse();irqcheck("reload_one",0);
  repeat(48)tick();irqcheck("held_high_no_reclock",0);
  low_samples(1);rise();irqcheck("short_one_rejected",0);
  low_samples(2);rise();irqcheck("short_two_rejected",0);
  pulse();irqcheck("third_sample_accepted",1);
  repeat(48)tick();irqcheck("irq_latched",1);
  wr(16'he001,0);irqcheck("enable_not_ack",1);
  wr(16'he000,0);irqcheck("disable_ack",0);
  pulse();pulse();irqcheck("disabled_no_irq",0);
  wr(16'hc000,3);wr(16'hc001,0);wr(16'he001,0);
  pulse();irqcheck("reload_three",0);pulse();irqcheck("count_two",0);
  wr(16'hc001,0);irqcheck("reload_deferred",0);
  pulse();irqcheck("reload_midcount",0);pulse();irqcheck("after_reload_two",0);pulse();irqcheck("after_reload_one",0);pulse();irqcheck("after_reload_zero",1);
  wr(16'he000,0);wr(16'hc000,0);wr(16'hc001,0);wr(16'he001,0);
  pulse();irqcheck("zero_latch_irq",1);wr(16'he000,0);wr(16'he001,0);pulse();irqcheck("zero_latch_repeats",1);
  reset_mapper();irqcheck("reset_clears_irq",0);
 end
 $fclose(fd);$display("RESULT checks=%0d irq_errors=%0d ticks=%0d",checks,errors,ticks);
 if(errors!=0)$fatal(1,"MMC3 directed IRQ assertions failed");
 $display("PASS MMC3 UNIT");$finish;
end
endmodule
