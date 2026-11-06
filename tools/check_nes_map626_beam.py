# SPDX-License-Identifier: MIT
"""Race pending work at the 247/248 boundary on the same accepted 1344 bytes."""
import argparse
import json
from pathlib import Path

from nes_raw506 import once
from test_nes_idle524_priority import case
from test_nes_tile532_edges import gate


def run(a):
    a.out.mkdir(parents=True)
    labels=json.loads((a.client/'labels.json').read_text())
    image=(a.client/'body.bin').read_bytes()
    pc=0x7e2000+image.index(bytes.fromhex('ad1242'),labels['prefix523']-0x7e2000)
    results=[]
    cases=[(247,1344,'late_stop'),(248,1152,'late_stop'),(247,1344,'head'),(247,1344,'both')]
    if a.suffix:
        cases=[(252,1152,mode) for mode in ('late_stop','head','both')]
    for line,limit,mode in cases:
        sub=argparse.Namespace(**vars(a))
        sub.out=a.out/f'line{line}-{mode}'
        sub.out.mkdir()
        def fixture(s,l):
            s=gate(s,l,line,'map',pc,limit,last_map_line=line)
            s=once(s,f'word(0x4004+word(0x1250)-8)>={limit}', 'word(0x4004+word(0x1250)-8)==1344')
            if a.suffix:
                s=once(s,'for i=0,math.min(length,1152)-1 do a[i+1]=string.char(emu.read(dest+i,',
                       'for i=0,math.min(length,1152)-1 do a[i+1]=string.char(emu.read(dest+length-1152+i,')
                s=once(s,'local offset=dest-(word(0x1034)','local offset=dest+length-1152-(word(0x1034)')
                s=once(s,'==source+1152 and word(0x4002+tail)==dest+1152','==source and word(0x4002+tail)==dest')
            s=once(s,'or assert(h)>640','or assert(h)<1000 or h>1150')
            return once(s,'local function loaded()',"""emu.addMemoryCallback(function()
 if not held or index~=held or armed or not tried532 then return end
 local st=emu.getState();local f=assert(io.open(ROOT..'/latch626.txt','w'))
 f:write(st['ppu.scanline'],',',st['memoryManager.hClock'] or st['ppu.hClock']);f:close()
end,emu.callbackType.read,0x2137)
local function loaded()""")
        r=case(sub,906,mode,edit_fixture=fixture)
        sampled,h=map(int,(sub.out/f'906-{mode}/latch626.txt').read_text().split(','))
        assert sampled==line and 1000<=h<1364 and r['size']==(limit if mode=='late_stop' else 0)
        if r['size']:
            assert line<=r['start_line']<=r['end_line']<262
        results.append(dict(sample_line=sampled,h=h,**r))
    (a.out/'result.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('trace','client','mesen','out'):
        p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--suffix',action='store_true')
    run(p.parse_args())
