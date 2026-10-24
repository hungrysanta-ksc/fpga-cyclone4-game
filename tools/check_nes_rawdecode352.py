# SPDX-License-Identifier: MIT
"""Actual decoder group-mask oracle, cold size transitions and invalidation."""
import argparse,binascii,json
from pathlib import Path
from nes_delta231 import sha
from probe_nes_arm264 import ARM
from probe_nes_decode280 import records,chunks,golden,encode280

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    arm=ARM(a.source/'decoder.elf',None);arm.call('reset280',[])
    def word(n):return int.from_bytes(arm.uc.mem_read(arm.symbols[n],4),'little')
    def feed(rr):
        for b in chunks(rr):
            arm.uc.mem_write(0x20018000,b);assert arm.call('block280',[0x20010000,0x20018000,len(b),binascii.crc_hqx(b,65535)])==1
        assert arm.call('complete280',[])==1
    rows=[];prior=None
    for f in range(905,976):
        rr=records(a.source/f'frame{f}.records');geo,raw=golden(f);feed(rr)
        expected=0xffffffff if rr[0][3]&2 else 0
        if prior is not None and not rr[0][3]&2:
            for i,(x,y) in enumerate(zip(prior,raw)):
                if x!=y:expected|=1<<((i%256)//8)
        assert word('source_groups352')==expected,(f,hex(expected),hex(word('source_groups352')))
        rows.append(dict(frame=f,mask=expected,raw_changed=sum(x!=y for x,y in zip(prior,raw)) if prior else len(raw)))
        prior=raw
    # Codec-only raw count transitions; geometry renderer is tested separately.
    old=geo;serial=71
    for count in (1,0,2):
        new=bytearray(old);new[4397]=count;new=bytes(new);raw=bytes([13])*(count*256);serial+=1
        rr=encode280(old,new,raw,prior,serial,serial);assert rr[0][3]&2;feed(rr)
        assert word('source_groups352')==0xffffffff
        assert bytes(arm.uc.mem_read(0x20010000,4398+len(raw)))==new+raw
        rows.append(dict(case='raw count transition',count=count,mask=word('source_groups352')));old=new;prior=raw
    snap=bytes(arm.uc.mem_read(0x20000000,0x40000))
    rr=encode280(old,old,prior,prior,serial+1,serial+1)
    for label,header in [('epoch',rr[0][:4]+(2).to_bytes(4,'little')+rr[0][8:]),('serial',rr[0][:12]+(0xffffffff).to_bytes(4,'little')+rr[0][16:])]:
        arm.uc.mem_write(0x20000000,snap);arm.uc.mem_write(0x20018000,header)
        assert arm.call('block280',[0x20010000,0x20018000,len(header),binascii.crc_hqx(header,65535)])==0
        assert word('source_groups352')==0xffffffff and arm.call('complete280',[])==0
        rows.append(dict(case=label+' rejects and invalidates'))
    arm.uc.mem_write(0x20000000,snap);arm.uc.mem_write(0x20018000,b'bad')
    assert arm.call('block280',[0x20010000,0x20018000,3,0])==0 and word('source_groups352')==0xffffffff
    arm.call('reset280',[]);assert word('source_groups352')==0xffffffff and arm.call('complete280',[])==0
    rows.append(dict(case='CRC failure and reset invalidate mask'))
    result=dict(passed=True,cases=rows,scope='71 actual source reconstructions plus codec-only count transitions and rejection guards',pins={str(a.source/'decoder.elf'):sha(a.source/'decoder.elf'),str(a.source/'nes_decode280.c'):sha(a.source/'nes_decode280.c')})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(dict(passed=True,cases=len(rows),warm_masks=[x for x in rows if x.get('frame') in (906,907)])))
if __name__=='__main__':main()
