"""Actual T65 executes original F869 LDA18/STA2001 and subsequent ROM reads.

Private reset/setup RAM stub configures bank78. PPU line/dot/name/scroll are
fixture controls; the 2001 write and rendering enable pipeline are live.
Actual native arbiter fill, CDC/70ns reader, byte comparison and STOP retained.
"""
import argparse,json
from pathlib import Path
import probe_nes_bonus699_cpu as prior

def prepare(board,rom,out,phase):
    prior.prepare(board,rom,out,phase,arbiter=True)
    p=out/'game147_tb.sv';s=p.read_text()
    s=s.replace('scenario<8','scenario<12').replace('scenario%4','scenario%12')
    s=s.replace('force dut.core.ppu.is_rendering_d=render699;force dut.core.ppu.is_rendering=render699;', '')
    s=s.replace('force dut.core.ppu.rendering_enabled=render699;','')
    s=s.replace('force dut.core.ppu.oam_bus=oam699;force dut.core.ppu.in_range=(scenario>=4);', '')
    s=s.replace("force dut.core.ppu.vram=15'd0", "force dut.core.ppu.vram=15'h1000;force dut.core.ppu.bg_name_table=8'h16;force dut.core.ppu.bg_patt=0")
    s=s.replace('force dut.core.ppu.ce=ce699;force dut.core.ppu.read=0;force dut.core.ppu.write=0;force tap_ce=ce699;', 'force dut.core.ppu.ce=ce699;force tap_ce=ce699;')
    s=s.replace("local_memory.cpu_ram.mem['h402]='h45", "local_memory.cpu_ram.mem['h402]='h00")
    s=s.replace("local_memory.cpu_ram.mem['h407]='h23", "local_memory.cpu_ram.mem['h407]='h78")
    s=s.replace("local_memory.cpu_ram.mem['h416]='h29;local_memory.cpu_ram.mem['h417]='hfb", "local_memory.cpu_ram.mem['h416]='h69;local_memory.cpu_ram.mem['h417]='hf8")
    s=s.replace("if(start699<0 && dut.core.cpu_rnw && dut.core.cpu_addr_full==24'hf794)start699=tick699;", "if(start699<0 && !dut.core.cpu_rnw && dut.core.cpu_addr_full==24'h2001)begin start699=tick699;dut.core.ppu.vram_a_byte=8'h61;end")
    s=s.replace('tick699-start699-9+(scenario%12)', 'tick699-start699+(scenario%12)')
    s=s.replace('249+step699/4','223+step699/4').replace('line699=start699<0?243:192','line699=start699<0?243:193')
    s=s.replace("dut.core.cpu_addr_full==24'h8001 && dut.core.cpu_dout==8'h7e", "dut.core.cpu_addr_full==24'h2001 && dut.core.cpu_dout==8'h18")
    s=s.replace("if(ppumem_addr!==dut.core.chr_linaddr || ppumem_addr!==22'h21fbe7 || native_chr_logical!==14'h1fe7)","if(ppumem_addr!==dut.core.chr_linaddr)")
    s=s.replace('    if(start699>=0)$display("CPU699', '''    if(rom_cpu_sample && !failed && cpumem_addr<25'h40000)
     if(!rom_cpu_valid || cpumem_din!==prg[cpumem_addr[17:0]])$fatal(1,"707 CPU independent byte mismatch");
    if(start699>=0)$display("CPU699''')
    s=s.replace('if(step699>=59)break;', 'if(step699>=79)break;')
    p.write_text(s,encoding='utf8',newline='\n')
    m=json.loads((out/'inputs.json').read_text());m.update(stage=707,scope=__doc__)
    m['sources']['game147_tb.sv']=prior.base.sha(p)
    (out/'inputs.json').write_text(json.dumps(m,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('board','rom','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--phase',type=float,default=3.5)
    a=p.parse_args();prepare(a.board,a.rom,a.out,a.phase)
