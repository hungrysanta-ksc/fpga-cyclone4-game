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
integer i,master_ticks=0,last_cpu_tick=-1,cpu_ticks=0,cpu_period_errors=0,unknown_bus=0;
integer frame=0,completed=0,pixels=0,pixel_errors=0,fetches=0,fetch_errors=0,table_changes=0;
integer fd,ft,fm,fc,table_base=0,previous_table=-1,x,tile,address,bitno,index;
reg collecting=0;
reg [5:0] expected_color;
reg [8:0] prevcycle=511,prevline=511;
always @(posedge clk) begin
 master_ticks=master_ticks+1;
 if($time>100000 && dut.core.cpu_ce)begin
  if(last_cpu_tick>=0 && master_ticks-last_cpu_tick!=12)cpu_period_errors=cpu_period_errors+1;
  last_cpu_tick=master_ticks;cpu_ticks=cpu_ticks+1;
  if($isunknown({dut.core.cpu_addr,dut.core.cpu_rnw,dut.core.internal_data_bus}))unknown_bus=unknown_bus+1;
 end
 if(cpumem_read)begin
  if(cpumem_addr<32768)cpumem_din<=prg[cpumem_addr];
  else if(cpumem_addr>=25'h380000 && cpumem_addr<25'h380800)cpumem_din<=ram[cpumem_addr[10:0]];
  else cpumem_din<=0;
 end
 if(cpumem_write && cpumem_addr>=25'h380000 && cpumem_addr<25'h380800)ram[cpumem_addr[10:0]]<=cpumem_dout;
 if(ppumem_read)begin
  if(ppumem_addr>=22'h200000 && ppumem_addr<22'h202000)ppumem_din<=chr[ppumem_addr[12:0]];
  else if(ppumem_addr>=22'h3a0000 && ppumem_addr<22'h3a0800)ppumem_din<=nt[ppumem_addr[10:0]];
  else ppumem_din<=0;
 end
 if(ppumem_write && ppumem_addr>=22'h3a0000 && ppumem_addr<22'h3a0800)nt[ppumem_addr[10:0]]<=ppumem_dout;
 // Observe before NBA: these are exactly the BgPainter latch conditions.
 // RTL latch cycles 6/8 correspond to Mesen read slots 5/7, not identical absolute time.
 if(dut.core.ppu_ce)begin
  if(dut.core.ppu.write && dut.core.ppu.ppu_ain==0)
   $fwrite(fc,"%0d\t%0d\t%0d\t%0d\n",master_ticks,scanline,cycle,dut.core.ppu.ppu_dbus);
  if(collecting && dut.core.ppu.bgp_en && (cycle[2:0]==6 || cycle[2:0]==0))begin
   $fwrite(ft,"%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\n",frame,scanline,cycle,master_ticks,dut.core.chr_addr,ppumem_addr,dut.core.ppu.vram_din,table_base);
   fetches=fetches+1;
   if($isunknown({dut.core.chr_addr,ppumem_addr,dut.core.ppu.vram_din}) || !ppumem_read || ppumem_addr!==22'h200000+dut.core.chr_addr || dut.core.ppu.vram_din!==chr[dut.core.chr_addr])fetch_errors=fetch_errors+1;
  end
 end
end
always @(negedge clk)begin
 if(cycle!=prevcycle || scanline!=prevline)begin
  if($time>60000000 && scanline==511 && cycle==1 && completed<4)begin
   collecting=1;frame=frame+1;table_base=dut.core.ppu.bg_patt ? 4096 : 0;
   if(previous_table>=0 && previous_table!=table_base)table_changes=table_changes+1;
   previous_table=table_base;
   fd=$fopen($sformatf("frame-%03d.hex",frame),"w");
   $fwrite(fm,"%0d\t%0d\t%0d\t%0d\n",frame,table_base,ram[1],master_ticks);
  end
  if(collecting && scanline<240 && cycle>=2 && cycle<=257)begin
   x=cycle-2;tile=((scanline/8)*32+x/8)&255;address=table_base+tile*16+scanline%8;bitno=7-x%8;
   index=((chr[address]>>bitno)&1)|(((chr[address+8]>>bitno)&1)<<1);
   case(index)0:expected_color=15;1:expected_color=33;2:expected_color=48;3:expected_color=22;endcase
   if(color!==expected_color || emphasis!==0)begin
    if(pixel_errors<8)$display("PIXEL_ERROR frame=%0d x=%0d y=%0d actual=%0d expected=%0d",frame,x,scanline,color,expected_color);
    pixel_errors=pixel_errors+1;
   end
   $fwrite(fd,"%02x\n",color);pixels=pixels+1;
  end
  if(collecting && scanline==240)begin
   collecting=0;completed=completed+1;$fclose(fd);
   $display("FRAME_COMPLETE frame=%0d table=%0d pixels=%0d errors=%0d",frame,table_base,pixels,pixel_errors);
  end
 end
 prevcycle=cycle;prevline=scanline;
end
initial begin
 #1000000;if(cpu_ticks<1000 || cpu_period_errors!=0 || unknown_bus!=0)$fatal(1,"early CPU clock/bus check failed");
end
initial begin
 repeat(14)begin #10000000;$display("PROGRESS time=%0t frames=%0d pixels=%0d pixel_errors=%0d fetch_errors=%0d",$time,completed,pixels,pixel_errors,fetch_errors);end
end
initial begin
 $readmemh("prg.hex",prg);$readmemh("chr.hex",chr);
 for(i=0;i<2048;i=i+1)begin ram[i]=0;nt[i]=0;end
 ft=$fopen("fetch.tsv","w");fm=$fopen("frames.tsv","w");fc=$fopen("control.tsv","w");
 #20000;reset_nes=0;cold_reset=0;
 #140000000;$fclose(ft);$fclose(fm);$fclose(fc);
 $display("RESULT frames=%0d pixels=%0d pixel_errors=%0d fetches=%0d fetch_errors=%0d table_changes=%0d cpu_ticks=%0d cpu_period_errors=%0d unknown_bus=%0d",completed,pixels,pixel_errors,fetches,fetch_errors,table_changes,cpu_ticks,cpu_period_errors,unknown_bus);
 if(completed!=4 || pixels!=245760 || pixel_errors!=0 || fetches!=65552 || fetch_errors!=0 || table_changes!=3 || cpu_period_errors!=0 || unknown_bus!=0)$fatal(1,"address-distinct fetch diagnostic failed");
 $display("PASS NES DIAGNOSTIC");$finish;
end
endmodule
