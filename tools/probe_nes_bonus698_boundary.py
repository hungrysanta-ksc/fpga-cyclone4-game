# SPDX-License-Identifier: MIT
"""Captured bonus sprite boundary, actual selected PPU/MMC3/CDC/70ns reader.

CPU instruction stream and collector/tile schedule are not replayed. OAM tuple
F8 FF FF FF and 192/261 bank5=7E come from exact-ROM reference06. CPU output
bus phases are explicit sensitivity inputs, not measured physical board phases.
"""
from pathlib import Path
import argparse,json
import probe_nes_bonus698 as base

BODY=r'''
 reg [8:0] dot698=249;reg render698=0,ce698=0;
 reg [23:0] cpuaddr698=0;reg [7:0] cpudata698=0,temp698=8'hff;
 reg rnw698=1;reg [4:0] div698=12;
 integer scenario,step698,change_tick,failed,requests,checked;
 reg [63:0] first_fault,first_ppu;
 task wr698(input [15:0] a,input [7:0] d);
  @(negedge clk);cpuaddr698=a;cpudata698=d;rnw698=0;div698=10;
  @(negedge clk);cpuaddr698=0;rnw698=1;div698=1;
 endtask
 initial begin
  $readmemh("prg.hex",prg);$readmemh("chr.hex",chr);
  force dut.core.ppu.cycle=dot698;force dut.core.ppu.scanline=9'd192;
  force dut.core.ppu.bg_patt1=0;force dut.core.ppu.obj_size1=1;force dut.core.ppu.obj_patt1=1;
  force dut.core.ppu.is_rendering_d=render698;force dut.core.ppu.is_rendering=render698;
  force dut.core.ppu.rendering_enabled=render698;
  force dut.core.ppu.oam_bus=temp698;force dut.core.ppu.in_range=0;
  force dut.core.ppu.vram=15'd0;force dut.core.ppu.read_2007_delayed=0;force dut.core.ppu.write_2007_delayed=0;
  force dut.core.ppu.ce=ce698;force dut.core.ppu.read=0;force dut.core.ppu.write=0;force tap_ce=ce698;
  force dut.core.cpu_addr_full=cpuaddr698;force dut.core.cpu_rnw=rnw698;force dut.core.cpu_dout=cpudata698;
  force dut.core.dma_aout_enable=0;force dut.core.div_cpu=div698;
  for(scenario=0;scenario<8;scenario++)begin
   @(negedge clk);reset_request=1;render698=0;ce698=0;dot698=249;cpuaddr698=0;rnw698=1;div698=12;
   repeat(8)@(negedge clk);reset_request=0;
   wait(!reset);wait(!dut.core.reset_noSS);wait(rom_ready);
   wr698(16'h8000,8'h45);wr698(16'h8001,scenario==0?8'h7e:8'h23);
   failed=0;requests=0;checked=0;first_fault=0;first_ppu=0;
   // 0 stable bank; 1 early write; 2..5 observed dot261 at four master phases;
   // 6 bank change after an unrelated CPU read; 7 unchanged bank plus CPU read.
   change_tick=scenario==1?4:(48+(scenario>=6?0:scenario-2));
   for(step698=0;step698<60;step698++)begin
    @(negedge clk);dot698=249+step698/4;ce698=(step698%4==3);
    render698=dot698>=257;
    temp698=(dot698==257)?8'hf8:8'hff;
    cpuaddr698=0;rnw698=1;div698=1;
    if(scenario>=6 && step698>=44 && step698<change_tick)begin cpuaddr698=24'hc123;div698=1;end
    if(scenario!=0 && scenario!=7 && step698==change_tick)begin cpuaddr698=24'h8001;cpudata698=8'h7e;rnw698=0;div698=10;end
    @(posedge clk);
    if(rom_request)requests++;
    if(fault_trigger&&!failed)begin first_fault=fault_context;first_ppu=ppu_fault_state154;failed=1;end
    if(ce698&&ppumem_read&&ppumem_addr>=22'h200000&&ppumem_addr<22'h220000&&!failed)begin
     if(!rom_ppu_valid||ppumem_din!==chr[ppumem_addr[16:0]])$fatal(1,"bad independent CHR byte");checked++;
    end
    if(step698>=40)$display("B698 scenario=%0d step=%0d dot=%0d sub=%0d logical=%h mapped=%h early=%b sample=%b valid=%b req=%b/%h ready=%b reply=%b/%h busy=%b age=%0d bank=%h rawwrite=%b hint=%b/%h fault=%b",
     scenario,step698,dot698,step698%4,native_chr_logical,ppumem_addr,rom_ppu_address_valid,
     tap_ce&&ppumem_read,rom_ppu_valid,rom_request,rom_address,rom_ready,rom_response,rom_response_address,
     rom_service.busy,rom_service.age,dut.core.multi_mapper.mapper.chr_bank_5,!rnw698,game147_prefetch_hint,game148_hint_physical,fault_trigger);
   end
   $display("CASE698 scenario=%0d failed=%0d error=%0d context=%h ppu=%h reads=%0d checked=%0d",scenario,failed,rom_error_code,first_fault,first_ppu,requests,checked);
   // STOP/common reset must cancel outstanding replies and sticky fault.
   @(negedge clk);reset_request=1;render698=0;ce698=0;cpuaddr698=0;rnw698=1;
   repeat(20)@(negedge clk);
   if(rom_fault||rom_request||rom_response||rom_cpu_valid||rom_ppu_valid||!psram_oe)$fatal(1,"STOP did not quiesce");
  end
  $display("DONE698 boundary STOP and independent bytes");$finish;
 end
 initial begin #10000000;$fatal(1,"boundary watchdog");end
endmodule
'''

def prepare(board,rom,out,phase):
 m=base.prepare(board,rom,out)
 p=out/'game147_tb.sv';s=p.read_text()
 s=s[:s.index(' integer target,unused,frame=0')]
 # Remove full-game pad declarations/instances; inputs are held unpressed.
 a=s.index(' wire game160_restart_hint');b=s.index(' wire tap_ce',a)
 s=s[:a]+''' wire game160_restart_hint,game147_prefetch_hint;wire [21:0] game148_hint_physical;
 wire [63:0] ppu_fault_state154;wire [13:0] native_chr_logical;
 wire [4:0] joypad1_data=0,joypad2_data=0;
'''+s[b:]
 s=s.replace('initial begin #3.5;',f'initial begin #{phase};')
 p.write_text(s+BODY,encoding='utf8',newline='\n')
 m['scope']=__doc__;m['memory_phase_ns']=phase;m['sources']['game147_tb.sv']=base.sha(p)
 (out/'inputs.json').write_text(json.dumps(m,indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['board','rom','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--phase',type=float,default=3.5)
 a=p.parse_args();prepare(a.board,a.rom,a.out,a.phase)
