# SPDX-License-Identifier: MIT
"""Actual ARM producer/cache lifetime tests; intercepted sink, not RTL timing."""
import argparse,binascii,json,struct
from pathlib import Path
from probe_nes_native289 import Producer
from probe_nes_arm264 import plans
from probe_nes_decode280 import records,chunks
from nes_bg293 import unbatch
from nes_bg295 import unbatch as unbatch295
from nes_delta231 import BASE,sha

def canonical(packets):
    other=[];maps=[]
    for p in packets:
        if p[0]!=9:
            other.append(p[:16]+bytes(4) if p[0]==7 else p[:2]+bytes(2)+p[4:])
            continue
        assert p[16]==3
        at=17
        while at<len(p):
            start=int.from_bytes(p[at:at+2],'little');n=p[at+2]*2;at+=3
            assert n and n<=64 and at+n<=len(p)
            maps.append((start,p[at:at+n]));at+=n
    # Packet sequences change if the first prepared packet has a different cut.
    return [p[:2]+bytes(2)+p[4:] for p in other],maps

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--last',type=int,default=975);a=ap.parse_args();d=a.out;d.mkdir(parents=True,exist_ok=False)
    arm=Producer(a.source/'output.elf',None);rows=[];guards=[]
    for name in ('reset259','reset285','reset280'):arm.call(name,[])
    arm.uc.mem_write(arm.symbols['palette285'],(BASE/'probes/nes-delta231/test07/palette.bin').read_bytes())
    arm.uc.mem_write(0x20010000,b'\xa5'*32768);_,groups=plans()
    word=lambda n:int.from_bytes(arm.uc.mem_read(arm.symbols[n],4),'little')
    def put(n,v):arm.uc.mem_write(arm.symbols[n],struct.pack('<I',v))
    def save():return bytes(arm.uc.mem_read(0x20000000,0x40000)),arm.uc.context_save(),len(arm.packets)
    def restore(x):arm.uc.mem_write(0x20000000,x[0]);arm.uc.context_restore(x[1]);del arm.packets[x[2]:];arm.fail_at=None
    for f in range(905,a.last+1):
        start=len(arm.packets);before=arm.instructions
        for b in chunks(records(BASE/f'probes/nes-joint284/test04/frame{f}.records')):
            arm.uc.mem_write(0x20028000,b);assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])
        for name in ('expand286','begin285','geometry_plan286','h2early286','input_commit286','begin_step286','begin_native290'):assert arm.call(name,[])
        for _ in range(2048):
            ok=arm.call('next_step286',[]);assert ok
            assert arm.call('service296',[]) and arm.call('tiles290',[0])
            if ok==2:break
        else:raise AssertionError('planner bound')
        actual=bytes(arm.uc.mem_read(arm.symbols['output285'],word('output_size285')))
        assert unbatch295(actual)==unbatch((BASE/f'probes/nes-joint284/test04/plans{f-904}.bin').read_bytes())
        assert arm.call('prepare289',[])
        # Directed ownership setup: this intercepted producer has no real E1.
        # Live RTL schedules separately exercise the actual acceptance path.
        put('map_issued327',0)
        buf=bytes(arm.uc.mem_read(arm.symbols['metadata317'],209))
        assert arm.call('prepare_map330',[])
        assert bytes(arm.uc.mem_read(arm.symbols['metadata317'],209))==buf and word('map_state330')==0
        put('map_issued327',1);slices=0
        while word('map_state330')!=2:
            assert slices<300 and arm.call('prepare_map330',[]);slices+=1
        assert word('map_used330')<=208
        snap=save()
        if f in (905,907):
            arm.call('stop286',[]);assert word('map_state330')==0 and word('left330')==0
            assert not arm.call('tiles290',[1]) and not arm.call('commit285',[])
            guards.append([f,'STOP clears partial/cached continuation and rejects commit']);restore(snap)
            arm.fail_at=len(arm.packets)+1
            assert not arm.call('tiles290',[1]) and not arm.call('commit285',[])
            submitted=len(arm.packets);assert not arm.call('tiles290',[1]) and len(arm.packets)==submitted
            guards.append([f,'ambiguous failed submit is not retried']);restore(snap)
        assert arm.call('tiles290',[1]) and word('map_state330')==3
        emitted=arm.packets[start:];assert canonical(emitted)==canonical(groups[f-904]),('canonical packets',f)
        assert arm.call('commit285',[])
        rows.append(dict(frame=f,packets=len(emitted),prepare_slices=slices,instructions=arm.instructions-before))
        print(json.dumps(rows[-1]),flush=True)
    assert arm.fixture_reads==0
    (d/'result.json').write_text(json.dumps(dict(passed=True,frames=rows,guards=guards,ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)),fixture_reads=0,scope=__doc__),indent=2)+'\n',newline='\n')

if __name__=='__main__':main()
