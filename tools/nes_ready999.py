"""Observe 907's final ARM source writes without changing its SPI or CPU schedule."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
import nes_page963
from nes_hdma990 import BASE, PACKED
from nes_objhint998 import hint
from replay_nes_supply905 import joint


def profile(temp,phase,paired):
    original=joint.Runtime.__init__
    offsets={"map":8704,"oam":12800,"cgram":13344,"hdma":13856}
    last={}
    captured={}
    def attach(cpu,*args):
        original(cpu,*args)
        base=cpu.video
        for name,offset in offsets.items():
            if name in cpu.layout["nes_native_video165"]:
                assert offset==cpu.layout["nes_native_video165"][name]
        def write(u,access,address,size,value,ctx):
            if cpu.generation!=907:return
            pos=address-base
            for i in range(pos,pos+size):
                last[i]=round(cpu.clock)
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,write,begin=base,end=base+14976)
        def snap(u,pc,size,ctx):
            if cpu.generation!=907:return
            assert not captured
            captured["entry"]=round(cpu.clock)
            captured["image"]=bytes(u.mem_read(base,14977)).hex()
            captured["last"]=dict(last)
        pc=cpu.syms["nes_sink212_seal"]
        cpu.u.hook_add(UC_HOOK_CODE,snap,begin=pc,end=pc)
    tag="999pair" if paired else "999ref"
    with patch.object(joint.Runtime,"__init__",attach),patch.object(nes_page963,"PACKED",PACKED):
        nes_page963.simulate(temp,phase,"cold",True,BASE,True,
            feedback=(lambda parent:hint(parent,True)) if paired else None,tag=tag,edition=966)
    captured["joined"]=[last[i] for i in range(6144,6144+441)]
    (temp/f"nes-{tag}-writes-p{phase}.json").write_text(json.dumps(captured))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path);p.add_argument("phase",type=int,choices=(1,2));p.add_argument("--paired",action="store_true")
    a=p.parse_args();profile(a.temp,a.phase,a.paired)
