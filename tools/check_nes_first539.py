# SPDX-License-Identifier: MIT
"""Differentially execute the linked planners on row identity, exception and patch boundaries."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from check_nes_game478 import Machine
from check_nes_supply485_arm import ARM


def probe(src, case):
    m=Machine(src,bytes(128))
    fields=m.layout['nes_native165']
    def put(name,data):
        m.u.mem_write(m.state+fields[name],data)

    # Adjacent lines can name different rows even when all 33 words match.
    rows=bytearray(y%8 for y in range(224))
    rows[4]=12
    maps=[0]*66
    if case in ('different_last_word','too_many_groups'):
        maps[-1]=1
    if case=='too_many_groups':
        for y in range(224):
            rows[y]|=(y%2)*8
    raster=[0x1e<<36]*224
    patches=0
    if case=='patch_edges':
        for row in (0,4,5,223):
            raster[row]=(1<<49)|(patches<<50)
            patches+=1
    exceptions=[(2*33<<6)|0o55] if case=='exception_fine' else []
    if case=='bad_exception':
        exceptions=[(2*33<<6)]*2
    put('rows',bytes(rows))
    put('maps',struct.pack('<66H',*maps))
    put('raster',struct.pack('<224Q',*raster))
    if exceptions:
        put('exceptions',struct.pack('<'+'I'*len(exceptions),*exceptions))
    put('counts',struct.pack('<6H',66,224,0,len(exceptions),224,32))
    put('ntiles',struct.pack('<H',2))
    put('tiles',struct.pack('<HBxHBx',0,1,1,1))
    put('state',bytes([4]))
    put('generation',struct.pack('<H',913))
    put('patch_count',bytes([patches]))
    assert m.call('nes_resident211_begin',[m.resident,1,1,913,m.writer|1,0])
    m.plans=[]
    ok=m.call('nes_native_video211_plan',[m.state,m.lut,m.video,m.resident])
    video=m.layout['nes_native_video165']
    data=bytes(m.u.mem_read(m.video,video['size']))
    assert bool(ok)==(case not in ('bad_exception','too_many_groups')),(case,data[video['error']])
    return dict(ok=bool(ok),error=data[video['error']],groups=data[video['groups']],
                video_SHA256=hashlib.sha256(data).hexdigest(),
                plans_SHA256=hashlib.sha256(json.dumps(m.plans).encode()).hexdigest())


def pause(src, short_final):
    m=ARM(src,'normal')
    flag=m.data_symbols['nes_cost471_available']
    m.u.mem_write(flag,struct.pack('<I',1))
    def run(reason,progress):
        start=m.instructions
        ok=m.call('nes_cost474_pause',[0,m.guard485|1,reason,int(progress)])
        return ok,m.instructions-start
    costs=[]
    for reason in range(3):
        ok,ticks=run(reason,False)
        budget=84*(64 if short_final and reason==2 else 128)
        # This isolated DWT fixture advances once per target instruction.
        assert ok and budget<=ticks<budget+250,(reason,ticks,budget)
        costs.append(ticks)
        assert run(reason,True)[1]<250
    m.u.mem_write(flag,bytes(4))
    assert run(2,False)[1]<250
    m.endpoint.mode='STOP_after_E9'
    m.endpoint.accepted=1
    assert run(2,False)[0]==0
    m.u.mem_write(flag,struct.pack('<I',1))
    assert run(2,False)[0]==0
    return costs


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arms',nargs=5,type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result={}
    for case in ('different_equal_rows','different_last_word','exception_fine','patch_edges','bad_exception','too_many_groups'):
        control,*new=[probe(src,case) for src in args.arms]
        assert all(item==control for item in new),case
        result[case]=control
    assert result['different_last_word']['groups']>result['different_equal_rows']['groups']
    result['quiet_instructions']=[pause(src,i>=3) for i,src in enumerate(args.arms)]
    args.out.write_text(json.dumps(result,indent=2)+'\n')
