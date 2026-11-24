"""Time finalized OAM and issue the complete, independently checked OAM stream at its producer boundary."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch
import nes_page963
from nes_hdma990 import BASE, PACKED
from nes_raw506 import once
from replay_nes_supply905 import joint, UC_HOOK_CODE
from unicorn import UC_HOOK_MEM_WRITE

ROOT=BASE.parent/"nes-oam992"
# The ARM layout is checked against every byte of the transmitted 544B OAM.
OAM_OFFSET=8192+512+4096


def prepare(mode):
    dst=ROOT/mode/"link"
    shutil.copytree(BASE/"link",dst)
    p=dst/"src/nes_native_sink165.c"
    s=p.read_text()
    if mode=="prefix":
        s=once(s,"op!=25 && op!=26 &&","op!=25 && op!=26 && op!=27 &&")
        s=once(s," if(op==26)op=10;"," if(op==27)op=8;\n if(op==26)op=10;")
        start=s.index(" if(!packet(s,24,3,0,p->cgram,32))")
        end=s.index(" p->prefix_sent972=true;",start)
        s=s[:end]+""" unsigned first=508;
 while(first>=4 && !memcmp(p->oam+first-4,p->oam+508,4))first-=4;
 if(first && first<=240 && 512-first>=128 && memcmp(p->oam+508,p->oam+510,2)){
  if(!packet(s,24,4,0,p->oam,first) ||
     !packet_wire(s,27,4,first,p->oam+508,4,512-first) ||
     !packet(s,24,4,512,p->oam+512,32))return false;
  p->oam_sent992=true;
 }
"""+s[end:]
        s=once(s," if(!oam227(s,p->oam))"," if(!p->oam_sent992 && !oam227(s,p->oam))")
        h=dst/"src/nes_native_video165.h"
        h.write_text(once(h.read_text(),"prefix_sent972;","prefix_sent972,oam_sent992;"),newline="\n")
    elif mode=="beforepal":
        s=once(s," if(p->prefix_sent972){"," if(p->prefix_sent972 && !oam227(s,p->oam))return false;\n if(p->prefix_sent972){")
        s=once(s," if(!oam227(s,p->oam))return false;"," if(!p->prefix_sent972 && !oam227(s,p->oam))return false;")
    else:raise ValueError(mode)
    p.write_text(s,newline="\n")


def run(temp,phase,mode):
    from check_nes_plan975 import directory
    ref=directory(temp,phase,"978returned","cold")
    expected=(ref/"colors636-911.bin").read_bytes()[512:]
    last={}
    marks={}
    original=joint.Runtime.__init__
    def install(cpu,*args):
        original(cpu,*args)
        base=cpu.video+OAM_OFFSET
        def write(u,access,addr,size,value,ctx):
            if cpu.generation==911:
                for i in range(max(0,addr-base),min(544,addr+size-base)):
                    last[i]=round(cpu.clock)
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,write,begin=base,end=base+543)
        def mark(key):
            def record(u,pc,size,ctx):
                if cpu.generation==911:
                    assert bytes(u.mem_read(base,544))==expected
                    marks[key]=round(cpu.clock)
            return record
        for name in ("nes_prefix972","nes_sink212_seal"):
            if name in cpu.syms:
                addr=cpu.syms[name];cpu.u.hook_add(UC_HOOK_CODE,mark(name),begin=addr,end=addr)
    arm={"ref":BASE,"store":BASE,"joint":ROOT/"prefix"}.get(mode,ROOT/mode)
    rom=ROOT/"store" if mode in ("store","joint") else PACKED
    with patch.object(nes_page963,"PACKED",rom), patch.object(joint.Runtime,"__init__",install):
        nes_page963.simulate(temp,phase,"cold",True,arm,True,tag="992"+mode,edition=966)
    assert len(last)==544 and len(expected)==544 and marks["nes_sink212_seal"]>=max(last.values())
    marks.update(full_final=max(last.values()),prefix_final=max(last[i] for i in range(176)),
                 fill_final=max(last[i] for i in range(176,512)),high_final=max(last[i] for i in range(512,544)))
    (temp/f"nes-oam992-{mode}-{phase}.json").write_text(json.dumps(marks,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("prepare","run"));p.add_argument("mode",choices=("ref","prefix","beforepal","store","joint"))
    p.add_argument("temp",type=Path,nargs="?");p.add_argument("phase",type=int,nargs="?",choices=(1,2))
    a=p.parse_args()
    if a.action=="prepare":
        if a.mode not in ("prefix","beforepal"):p.error("only ARM variants require preparation")
        prepare(a.mode)
    else:run(a.temp,a.phase,a.mode)
