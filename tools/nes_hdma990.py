"""Timestamp the actual producer writes and compare the one-row table-first receiver."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_page963
from nes_head980 import baseline
from replay_nes_supply905 import joint, UC_HOOK_CODE
from unicorn import UC_HOOK_MEM_WRITE
from nes_blank960 import PACKED

BASE=baseline("returned")
ROOT=BASE.parent/"nes-hdma990"
ROM=ROOT/"rom"


def run(temp,phase,mode):
    original=joint.Runtime.__init__
    writes={}
    snapshot={}
    def instrument(cpu,*args):
        original(cpu,*args)
        base=cpu.video
        def written(u,access,address,size,value,ctx):
            if cpu.generation!=911:return
            for i in range(address-base,address-base+size):
                writes[i]=cpu.clock
        def mark(u,pc,size,ctx):
            if cpu.generation!=911:return
            sizes=bytes(u.mem_read(base+2048+244,6))
            lengths=[int.from_bytes(sizes[i:i+2],"little") for i in (0,2,4)]
            assert lengths==[21,21,21]
            raw=[k*64+plane*16+lane for k in range(32) for plane in range(3) for lane in (0,1)]
            table=[2048+b*81+i for b,n in enumerate(lengths) for i in range(n)]
            snapshot.update(raw_pixels_final=max(writes[i] for i in raw),
                            active_table_final=max(writes[i] for i in table),
                            lengths_final=max(writes[i] for i in range(2048+244,2048+250)),
                            sink_enter=cpu.clock,active_lengths=lengths)
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,written,begin=base,end=base+4096+192-1)
        at=cpu.syms["nes_sink212_seal"]
        cpu.u.hook_add(UC_HOOK_CODE,mark,begin=at,end=at)
    path=BASE if mode=="ref" else ROOT/mode
    rom=PACKED if mode=="ref" else ROOT/"repeat" if mode.startswith(("repeat","rle")) else (ROOT/"compact" if mode.removeprefix("safe") in ("front","packed","gap") else ROM)
    with patch.object(joint.Runtime,"__init__",instrument),patch.object(nes_page963,"PACKED",rom):
        nes_page963.simulate(temp,phase,"cold",True,path,True,tag="990"+mode,edition=966)
    snapshot["packed_raw_final"]=max(writes[i] for i in range(4096,4096+192))
    (temp/f"nes-hdma990-{mode}-p{phase}.json").write_text(json.dumps(snapshot,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path);p.add_argument("phase",type=int);p.add_argument("mode")
    a=p.parse_args();run(a.temp,a.phase,a.mode)
