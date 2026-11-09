"""Compare698 short pulses with CPU-width writes, using the unchanged consumer.

Pulse tests deliberately permit physically late writes: do not relabel their
remaining deadline errors as passing data. Actual T65 execution is separate.
"""
from pathlib import Path
import argparse,json
import probe_nes_bonus698_boundary as boundary
import probe_nes_bonus698 as base

def prepare(board,rom,out,phase,mode):
    boundary.prepare(board,rom,out,phase)
    p=out/'game147_tb.sv';s=p.read_text()
    if mode in ('width','stop'):
        old="if(scenario!=0 && scenario!=7 && step698==change_tick)begin cpuaddr698=24'h8001;cpudata698=8'h7e;rnw698=0;div698=10;end"
        new="if(scenario!=0 && scenario!=7 && step698>=change_tick-9 && step698<=change_tick+2)begin cpuaddr698=24'h8001;cpudata698=8'h7e;rnw698=0;div698=10+step698-change_tick;end"
        assert old in s;s=s.replace(old,new)
    if mode=='stop':
        s=s.replace('if(ce698&&ppumem_read', 'if(!reset&&ce698&&ppumem_read')
        s=s.replace('if(rom_request)requests++;', '''if(step698==47+2*(scenario%4))begin
     #0.001;reset_request=1;#0.001;
     if(rom_request||rom_response||rom_cpu_valid||rom_ppu_valid||!psram_oe)$fatal(1,"mid-read STOP was not immediate");
     $display("STOP699 scenario=%0d step=%0d quiescent=1",scenario,step698);
    end
    if(rom_request)requests++;''')
    p.write_text(s,encoding='utf8',newline='\n')
    m=json.loads((out/'inputs.json').read_text());m['stage']=699;m['mode']=mode
    m['sources']['game147_tb.sv']=base.sha(p)
    (out/'inputs.json').write_text(json.dumps(m,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('board','rom','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--phase',type=float,default=3.5)
    p.add_argument('--mode',choices=['pulse','width','stop'],required=True)
    a=p.parse_args();prepare(a.board,a.rom,a.out,a.phase,a.mode)
