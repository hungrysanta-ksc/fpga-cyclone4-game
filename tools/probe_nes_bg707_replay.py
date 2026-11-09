"""Replay natural-boot193-line PPU history with bounded CPU phase sensitivity.

PPU scroll/name/PPUDATA-pipeline and CPU bus are recorded stimulus. Latch,
mapper, request arbitration, CDC, physical reader and consumed bytes are live.
This is not instruction execution, nor proof of the missing705 prior history.
"""
import argparse,json,re
from pathlib import Path
import probe_nes_bonus698_boundary as base

def prepare(board,rom,trace,out,phase,frame):
    base.prepare(board,rom,out,phase)
    rows=[]
    for line in trace.read_text().splitlines():
        if f'frame={frame} ' not in line or not line.startswith('# BG707 '):continue
        d=dict(re.findall(r'(\w+)=([^ ]+)',line));rows.append(d)
    assert len(rows)==124
    init=[]
    for i,d in enumerate(rows):
        addr,rnw,data=d['cpu'].split('/');ppu=int(d['ppu'],16)
        init.append(f"  dots[{i}]=9'd{d['dot']};ces[{i}]=1'b{d['ce']};cas[{i}]=24'h{addr};divs[{i}]=5'd{d['div']};names[{i}]=8'h{d['name']};vrams[{i}]=15'h{d['vram']};pipes[{i}]=5'd{(ppu>>37)&31};")
    p=out/'game147_tb.sv';s=p.read_text();s=s[:s.index(' reg [8:0] dot698')]
    body=r'''
 reg [8:0] dots[0:123],dot707;reg ces[0:123],ce707=0;
 reg [23:0] cas[0:123],ca707=0;reg [4:0] divs[0:123],div707=12,pipes[0:123],pipe707=0;
 reg [7:0] names[0:123],name707=0;reg [14:0] vrams[0:123],vram707=0;
 reg rnw707=1,render707=0;reg [7:0] data707=0;
 integer scenario,i,j,failed,checked,first;reg [63:0] fc,pc;
 task wr707(input [15:0] a,input [7:0] d);
  @(negedge clk);ca707=a;data707=d;rnw707=0;div707=10;
  @(negedge clk);ca707=0;rnw707=1;div707=12;
 endtask
 initial begin
  $readmemh("prg.hex",prg);$readmemh("chr.hex",chr);
INIT
  force dut.core.ppu.cycle=dot707;force dut.core.ppu.scanline=9'd193;
  force dut.core.ppu.bg_patt1=0;force dut.core.ppu.bg_patt=0;
  force dut.core.ppu.is_rendering_d=render707;force dut.core.ppu.rendering_enabled=render707;
  force dut.core.ppu.re_sr={3{render707}};
  force dut.core.ppu.bg_name_table=name707;force dut.core.ppu.vram0.vram_v=vram707;
  force dut.core.ppu.read_2007_delayed=pipe707;force dut.core.ppu.write_2007_delayed=0;
  force dut.core.ppu.ce=ce707;force tap_ce=ce707;
  force dut.core.cpu_addr_full=ca707;force dut.core.cpu_rnw=rnw707;force dut.core.cpu_dout=data707;
  force dut.core.div_cpu=div707;force dut.core.dma_aout_enable=0;
  for(scenario=-3;scenario<=3;scenario++)begin
   @(negedge clk);reset_request=1;render707=0;ce707=0;ca707=0;rnw707=1;div707=12;pipe707=0;dot707=210;
   repeat(8)@(negedge clk);reset_request=0;wait(!reset);wait(!dut.core.reset_noSS);wait(rom_ready);
   wr707(16'h8000,0);wr707(16'h8001,8'h78);wr707(16'h8000,7);wr707(16'h8001,8'h18);
   failed=0;checked=0;first=-1;fc=0;pc=0;
   // Start from a real cached low plane before the recorded interval.
   rom_service.ppu_cached=1;rom_service.ppu_tag=17'h1efc8;rom_service.ppu_byte=chr['h1efc8];
   rom_service.ppu_previous_cached=1;rom_service.ppu_previous_tag=17'h1efc0;rom_service.ppu_previous_byte=chr['h1efc0];
   dut.core.ppu.vram_a_byte=8'hc8;
   rom_service.cpu_line_valid[3]=1;rom_service.cpu_line_tag[3]=15'h6107;rom_service.cpu_line_byte[3]=prg['h3083b];
   for(i=0;i<124;i++)begin
    @(negedge clk);j=i-scenario;if(j<0)j=0;if(j>123)j=123;
    render707=1;dot707=dots[i];ce707=ces[i];ca707=cas[j];div707=divs[j];name707=names[i];vram707=vrams[i];pipe707=pipes[i];
    @(posedge clk);
    if(fault_trigger&&!failed)begin failed=1;first=i;fc=fault_context;pc=ppu_fault_state154;end
    if(ce707&&ppumem_read&&ppumem_addr>=22'h200000&&ppumem_addr<22'h220000&&!failed)begin
     if(!rom_ppu_valid||ppumem_din!==chr[ppumem_addr[16:0]])$fatal(1,"707 replay CHR mismatch");checked++;
    end
    $display("R707 scenario=%0d i=%0d dot=%0d div=%0d pipe=%h cpu=%h chr=%h hint=%b/%h req=%b/%h response=%b/%h age=%0d fault=%b ppu=%h",scenario,i,dot707,div707,pipe707,ca707,ppumem_addr,rom_service.ppu_prefetch_valid,game148_hint_physical,rom_request,rom_address,rom_response,rom_response_address,rom_service.age,fault_trigger,ppu_fault_state154);
   end
   $display("CASE707REPLAY shift=%0d failed=%0d error=%0d checked=%0d first=%0d context=%h ppu=%h",scenario,failed,rom_error_code,checked,first,fc,pc);
   @(negedge clk);reset_request=1;render707=0;ce707=0;
   #0.001;if(rom_request||rom_response||rom_cpu_valid||rom_ppu_valid||!psram_oe)$fatal(1,"707 immediate STOP failed");
   repeat(16)@(negedge clk);
   if(rom_request||rom_response||rom_cpu_valid||rom_ppu_valid||!psram_oe)$fatal(1,"707 stale reply");
  end
  $display("DONE698 recorded background history sensitivity");$finish;
 end
 initial begin #10000000;$fatal(1,"707 replay watchdog");end
endmodule
'''.replace('INIT','\n'.join(init))
    p.write_text(s+body,encoding='utf8',newline='\n')
    m=json.loads((out/'inputs.json').read_text());m.update(stage=707,scope=__doc__,trace_sha256=base.base.sha(trace),frame=frame)
    m['sources']['game147_tb.sv']=base.base.sha(p)
    (out/'inputs.json').write_text(json.dumps(m,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('board','rom','trace','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--phase',type=float,default=3.5);p.add_argument('--frame',type=int,default=16)
    a=p.parse_args();prepare(a.board,a.rom,a.trace,a.out,a.phase,a.frame)
