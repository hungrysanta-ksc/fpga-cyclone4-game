# SPDX-License-Identifier: MIT
"""Independent malformed-input, cancellation and expired-scratch checks."""
import argparse,binascii,json,struct
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_planner285 import Planner
from probe_nes_decode280 import chunks,records


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--arm',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
    elf=a.arm/'planner.elf';arm=Planner(elf,None);arm.call('reset285',[]);arm.call('reset280',[])
    palette=BASE/'probes/nes-delta231/test07/palette.bin';arm.uc.mem_write(arm.symbols['palette285'],palette.read_bytes())
    rr=records(BASE/'probes/nes-joint284/test04/frame905.records');bb=chunks(rr);checks=[]
    def save():return bytes(arm.uc.mem_read(0x20000000,0x40000)),arm.uc.context_save()
    def restore(x):arm.uc.mem_write(0x20000000,x[0]);arm.uc.context_restore(x[1])
    for i,b in enumerate(bb):
        arm.uc.mem_write(0x20028000,b)
        if i==len(bb)-1:
            before=save();bad=bytearray(b);bad[-1]^=1;arm.uc.mem_write(0x20028000,bytes(bad))
            assert not arm.call('block286',[0x20028000,len(bad),binascii.crc_hqx(bad,65535)])
            assert not arm.call('input_commit286',[]);checks.append('late stream CRC despite correct outer block CRC');restore(before)
        assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])
    snapshot=save();history=arm.symbols['history286']
    mutations=[('map count zero',4385,b'\x00\x00'),('object count129',4389,b'\x81\x00'),('palette count invalid',4395,b'\x03\x00'),('raw count3',4397,b'\x03'),('map high bit',0,b'\x00\x80'),('object reserved bits',2342,b'\xff\xff'),('display mask',4320,b'\x00'),('raster reserved bits',3872,b'\x00\xc0'),('raster impossible raw index',3872,b'\x00\x3c')]
    for name,offset,value in mutations:
        restore(snapshot);arm.uc.mem_write(history+offset,value);assert not arm.call('expand286',[]),name;checks.append(name)
    restore(snapshot);assert arm.call('expand286',[]) and arm.call('begin285',[]) and arm.call('geometry_plan286',[]) and arm.call('h2early286',[])
    ready=save();assert not arm.call('begin_step286',[]);checks.append('raw not committed before start')
    arm.call('stop286',[]);assert not arm.call('input_commit286',[]) and not arm.call('next_step286',[]) and not arm.word('calls285');checks.append('STOP after H2 freezes plan')
    restore(ready);assert arm.call('input_commit286',[])
    # Raw range validation remains a separate start barrier even if a direct
    # caller bypasses the source decoder. Identify the unique committed512B
    # copy in the actual input struct, asserting uniqueness before mutation.
    raw=bytes(arm.uc.mem_read(history+4398,512));native=bytes(arm.uc.mem_read(arm.symbols['input285'],9880));matches=[i for i in range(len(native)-511) if native[i:i+512]==raw]
    assert len(matches)==1;raw_address=arm.symbols['input285']+matches[0];rawready=save();arm.uc.mem_write(raw_address,b'\x40');assert not arm.call('begin_step286',[]);checks.append('direct raw pixel64')
    restore(rawready);assert arm.call('begin_step286',[]);started=save();v=arm.symbols['video285']
    arm.uc.mem_write(v+8,bytes([0xa5])*(8192-8));arm.uc.mem_write(v+8192,bytes([0x5a])*512)
    steps=0
    while True:
        ok=arm.call('next_step286',[]);assert ok;steps+=1
        if ok==2:break
        assert steps<=32
    out=bytes(arm.uc.mem_read(arm.symbols['output285'],arm.word('output_size285')))
    assert out==(BASE/'probes/nes-joint284/test04/plans1.bin').read_bytes()
    layout=[arm.call('layout285',[i]) for i in range(7)]
    actual=bytes(arm.uc.mem_read(v+layout[0],4096))+bytes(arm.uc.mem_read(v+layout[1],512))+bytes(arm.uc.mem_read(v+layout[2],544))+bytes(arm.uc.mem_read(v+layout[1]+512,1121))+bytes(arm.uc.mem_read(v,2291))+bytes(arm.uc.mem_read(v+2292,6))
    assert actual==(BASE/'probes/nes-wholepath247/jointdecode-test02/run/expected-1.bin').read_bytes();checks.append('expired BG/OBJ scratch poison exact plan and8570B metadata')
    restore(started);assert arm.call('next_step286',[])==1;count=arm.word('calls285');arm.call('stop286',[]);assert not arm.call('next_step286',[]) and arm.word('calls285')==count;checks.append('STOP between groups freezes callbacks')
    result=dict(passed=True,checks=checks,ELF_sha256=sha(elf),script_sha256=sha(Path(__file__)),scope=__doc__)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
