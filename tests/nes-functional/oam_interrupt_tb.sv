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
reg started=0;
integer fo,j,fp;
reg irq_in=0,nmi_in=0,armed=0;
integer active_case=0,step=-1,record=0,arrival=0,mode=0;
reg [15:0] anchor;
// Only interrupt inputs are forced; real DmaController owns pause and bus.
initial begin force dut.core.mapper_irq=irq_in;force dut.core.nmi=nmi_in;end
always @(negedge clk)begin
 if(reset_nes)begin active_case=0;step=-1;armed=0;irq_in=0;nmi_in=0;end
 else if(dut.core.cpu_ce)begin
  if(ram[0]!=active_case && ram[0]>0 && ram[0]<255)begin
   active_case=ram[0];record=16'h7400+(active_case-1)*8;
   anchor={prg[record+1],prg[record]};arrival={prg[record+3],prg[record+2]};mode=prg[record+4];
   armed=0;irq_in=0;nmi_in=0;step=-1;
  end
  if(!armed && active_case>0 && dut.core.cpu_addr==16'h4014 && !dut.core.cpu_rnw)begin armed=1;step=0;end
  else if(armed)step=step+1;
  if(armed && step==arrival)begin if(mode==1 || mode==3)irq_in=1;if(mode==2 || mode==3)nmi_in=1;end
  if(armed && step==arrival+1)nmi_in=0;
  if(dut.core.cpu_addr==2 && !dut.core.cpu_rnw && !dut.core.pause_cpu)irq_in=0;
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
 if(started && dut.core.cpu_ce)
  $fwrite(fp,"%0d %0d %0d %0d %0d %0d %0d %0d %0d %0d\n",tick,ram[0],step,irq_in,nmi_in,dut.core.pause_cpu,dut.core.cpu_addr,dut.core.cpu_rnw,dut.core.cpu_rnw ? dut.core.internal_data_bus : dut.core.cpu_dout,dut.core.odd_or_even);
 if(started && dut.core.cart_ce)begin
  if(last>=0 && tick-last!=12)badperiod=badperiod+1;last=tick;
  if($isunknown({dut.core.cpu_addr,dut.core.cpu_rnw,dut.core.internal_data_bus}))unknown_bus=unknown_bus+1;
  $fwrite(fd,"%0d %0d %0d %0d %0d %0d %0d %0d %0d %0d\n",tick,dut.core.addr,dut.core.mr_int,dut.core.mr_int ? dut.core.internal_data_bus : dut.core.dbus,ram[0],dut.core.cpu_addr,dut.core.cpu_rnw,dut.core.pause_cpu,dut.core.dma_aout_enable,dut.core.odd_or_even);
  if(!dut.core.cpu_rnw && dut.core.cpu_addr==16'h20 && !dut.core.pause_cpu)begin
   $fwrite(fo,"E %0d %0d %0d\n",ram[0],ram[16],dut.core.ppu.spriteeval.oam_addr);
   $fwrite(fo,"I %0d %0d %0d\n",ram[0],ram[3],ram[4]);
   for(j=0;j<256;j=j+1)$fwrite(fo,"O %0d %0d %0d\n",ram[0],j,dut.core.ppu.spriteeval.oam[j]);
  end
  if(dut.core.prg_write && dut.core.prg_addr==0)begin
   if(dut.core.prg_din!=255)begin
    if(dut.core.prg_din!=seen+1)$fatal(1,"Case progress mismatch");seen=seen+1;
   end else begin
    if(seen!=24 || badperiod!=0 || unknown_bus!=0)$fatal(1,"OAM interrupt diagnostic completion invalid seen=%0d period=%0d unknown=%0d",seen,badperiod,unknown_bus);
    $fclose(fd);$fclose(fo);$fclose(fp);$display("RESULT oam_interrupt_cases=%0d period_errors=%0d unknown_bus=%0d",seen,badperiod,unknown_bus);
    $display("PASS NES DIAGNOSTIC");$finish;
   end
  end
 end
end
initial begin
 $readmemh("prg.hex",prg);for(i=0;i<2048;i=i+1)ram[i]=0;
 fp=$fopen("pins.tsv","w");fd=$fopen("dma-bus.tsv","w");fo=$fopen("oam.tsv","w");#20000;reset_nes=0;cold_reset=0;
 #20000000;$fatal(1,"OAM interrupt diagnostic timeout");
end
endmodule
