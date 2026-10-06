// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module nes_tb;
reg clk=0;always #23.280423 clk=~clk;
reg reset_nes=1,cold_reset=1;
reg [7:0] cpumem_din=0,ppumem_din=0;
reg [4:0] joypad1_data=0,joypad2_data=0;
wire [24:0] cpumem_addr;wire [21:0] ppumem_addr;
wire cpumem_read,cpumem_write,ppumem_read,ppumem_write;
wire [7:0] cpumem_dout,ppumem_dout;
wire [5:0] color;wire [2:0] emphasis;
wire [8:0] cycle,scanline;wire [15:0] sample;
nes_probe dut(.*);
reg [7:0] prg[0:32767],ram[0:2047];
reg started=0,irq_in=0,nmi_in=0,stall_in=0,armed=0,pass_done=0;
integer pass=0,active_case=0,step=-1,record=0,stall_start=0,mode=0;
reg [15:0] anchor;
initial begin force dut.core.mapper_irq=irq_in;force dut.core.nmi=nmi_in;force dut.core.pause_cpu=stall_in;end
always @(negedge clk)begin
 if(reset_nes)begin active_case=0;step=-1;armed=0;irq_in=0;nmi_in=0;stall_in=0;end
 else if(dut.core.cpu_ce)begin
  if(ram[0]!=active_case && ram[0]>0 && ram[0]<255)begin
   active_case=ram[0];record=16'h7400+(active_case-1)*8;
   anchor={prg[record+1],prg[record]};stall_start=prg[record+2];mode=prg[record+3];
   armed=0;irq_in=0;nmi_in=0;stall_in=0;step=-1;
  end
  if(!armed && active_case>0 && dut.core.cpu_addr==anchor && dut.core.cpu_rnw)begin armed=1;step=0;end
  else if(armed)step=step+1;
  if(pass==1 && armed)begin
   stall_in=(step>=stall_start && step<stall_start+3);
   if(step==stall_start+1)begin if(mode==1 || mode==3)irq_in=1;if(mode==2 || mode==3)nmi_in=1;end
   if(step==stall_start+2)nmi_in=0;
  end
  if(dut.core.cpu_addr==2 && !dut.core.cpu_rnw)irq_in=0;
 end
end
integer i,fd,tick=0,last=-1,badperiod=0,unknown_bus=0,seen=0;
always @(posedge clk)begin
 tick=tick+1;
 if(cpumem_read)begin
  if(cpumem_addr<32768)cpumem_din<=prg[cpumem_addr];
  else if(cpumem_addr>=25'h380000 && cpumem_addr<25'h380800)cpumem_din<=ram[cpumem_addr[10:0]];
  else cpumem_din<=0;
 end
 if(cpumem_write && cpumem_addr>=25'h380000 && cpumem_addr<25'h380800)ram[cpumem_addr[10:0]]<=cpumem_dout;
 if(!reset_nes && dut.core.cart_ce && dut.core.cpu_addr==16'h8000 && dut.core.cpu_rnw && dut.core.internal_data_bus==8'h78)started=1;
 if(started && !pass_done && dut.core.cpu_ce)begin
  if(last>=0 && tick-last!=12)badperiod=badperiod+1;last=tick;
  if($isunknown({dut.core.cpu_addr,dut.core.cpu_rnw,dut.core.internal_data_bus}))unknown_bus=unknown_bus+1;
  $fwrite(fd,"B %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d\n",pass,tick,dut.core.cpu_addr,dut.core.cpu_rnw,dut.core.cpu_rnw ? dut.core.internal_data_bus : dut.core.cpu_dout,ram[0],step,!stall_in,irq_in,nmi_in);
  if(!dut.core.cpu_rnw && dut.core.cpu_addr==16'h20)$fwrite(fd,"E %0d %0d %0d %0d %0d\n",pass,ram[0],ram[16],ram[17],ram[18]);
  if(!dut.core.cpu_rnw && dut.core.cpu_addr==0)begin
   if(dut.core.cpu_dout!=255)begin
    if(dut.core.cpu_dout!=seen+1)$fatal(1,"Case progress mismatch");seen=seen+1;
   end else begin
    if(seen!=56 || badperiod!=0 || unknown_bus!=0)$fatal(1,"Branch diagnostic completion invalid seen=%0d period=%0d unknown=%0d",seen,badperiod,unknown_bus);
    $display("PASS_COMPLETE pass=%0d cases=%0d period_errors=%0d unknown_bus=%0d",pass,seen,badperiod,unknown_bus);pass_done=1;
   end
  end
 end
end
initial begin
 $readmemh("prg.hex",prg);for(i=0;i<2048;i=i+1)ram[i]=0;
 fd=$fopen("rdy.tsv","w");#20000;reset_nes=0;cold_reset=0;
 wait(pass_done);reset_nes=1;cold_reset=1;started=0;
 #1;for(i=0;i<2048;i=i+1)ram[i]=0;
 pass=1;pass_done=0;seen=0;last=-1;badperiod=0;unknown_bus=0;
 #20000;reset_nes=0;cold_reset=0;
 wait(pass_done);$fclose(fd);$display("PASS NES DIAGNOSTIC");$finish;
end
initial begin #10000000;$fatal(1,"RDY diagnostic timeout");end
endmodule
