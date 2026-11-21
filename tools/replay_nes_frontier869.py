"""Observe row completion, map writes and new BG slot ownership on the MMC866 link."""
import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'.tools/arm259-python'))
from replay_nes_ack861 import joint, replay
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE


def trace(temp, phase, tag):
    reference=temp/f'nes-tile821-demo-jointmirror-p{phase}-866-on'
    arm=ROOT.parent/'probes/nes-trial866/link/src'
    baseline=json.loads((reference/'joint.json').read_bytes())
    assert hashlib.sha256((arm/'obj-nes-100/firmware.stm').read_bytes()).hexdigest()==baseline['firmware_SHA256']
    data=json.loads((ROOT/'analysis/map868-strip.json').read_bytes())
    pages=defaultdict(set)
    for r in data['phases'][phase-1]['frames']:pages[r['g']].add(r['page']//2048)
    samples=defaultdict(lambda:dict(groups=[],closed=[],writes=[0]*64,changes=[0]*64,slots={},offers=[]))
    original=joint.Runtime.__init__
    def init(cpu,args,link):
        original(cpu,args,link)
        video=cpu.layout['nes_native_video165']
        start=cpu.video+video['map']
        used=cpu.resident+cpu.layout['nes_resident211']['used']
        def written(u,access,addr,size,value,_):
            g=cpu.generation
            if g not in pages:return
            offset=addr-start
            lo=max(0,-offset)
            hi=min(size,4096-offset)
            if lo>=hi:return
            old=bytes(u.mem_read(addr,size))
            new=(value%(1<<(size*8))).to_bytes(size,'little')
            for j in range(lo,hi):
                row=(offset+j)//64
                if row//32 not in pages[g] or row%32>=23:continue
                samples[g]['writes'][row]=cpu.clock
                if old[j]!=new[j]:
                    samples[g]['changes'][row]=cpu.clock
        def owned(u,access,addr,size,value,_):
            g=cpu.generation
            if g not in pages:return
            old=int.from_bytes(u.mem_read(addr,size),'little')
            rising=value & ~old & ((1<<(8*size))-1)
            while rising:
                bit=rising & -rising
                slot=(addr-used)*8+bit.bit_length()-1
                if slot<1024:
                    samples[g]['slots'][slot]=cpu.clock
                rising-=bit
        def event(field):
            def observe(u,pc,size,_):
                g=cpu.generation
                if g in pages:
                    samples[g][field].append(cpu.clock)
            return observe
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,written,begin=start,end=start+4095)
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,owned,begin=used,end=used+127)
        # MMC866 DWARF nes_planner211.c lines 191 and 201. The firmware hash
        # binds the two PCs. Row completion precedes optional tile service.
        cpu.u.hook_add(UC_HOOK_CODE,event('closed'),begin=0x08020db6,end=0x08020db6)
        cpu.u.hook_add(UC_HOOK_CODE,event('offers'),begin=0x08020416,end=0x08020416)
        counter=cpu.data_symbols['nes_cost474_groups']
        def group(u,access,addr,size,value,_):
            if cpu.generation in pages:samples[cpu.generation]['groups'].append(cpu.clock)
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,group,begin=counter,end=counter+3)
    with patch.object(joint.Runtime,'__init__',init):
        replay(temp,855,phase,128,high=True,arm_override=arm,tag_override=tag)
    folder=temp/f'nes-tile821-demo-jointmirror-p{phase}-{tag}'
    (folder/'frontier869.json').write_text(json.dumps(samples))
    actual=json.loads((folder/'joint.json').read_bytes())
    assert actual==baseline
    for name in ('packets.jsonl','window.csv'):
        assert (reference/name).read_bytes()==(folder/name).read_bytes(),name
    assert set(samples)==set(pages)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('phase',type=int,choices=(1,2))
    parser.add_argument('tag')
    trace(**vars(parser.parse_args()))
