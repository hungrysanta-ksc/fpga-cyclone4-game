# SPDX-License-Identifier: MIT
"""Exercise a full large grant and both priority inputs on the candidate binary."""
import argparse
import json
from pathlib import Path

from nes_raw506 import once
from test_nes_idle524_priority import case
from test_nes_tile532_edges import gate, width
from test_nes_map526_priority import map_fixture
from test_nes_tile532_priority import prepare


def run(a):
    labels=json.loads((a.client/'labels.json').read_text())
    body=(a.client/'body.bin').read_bytes()
    beam_pc=0x7e2000+body.index(bytes.fromhex('ad1242'), labels['prefix523']-0x7e2000)
    a.out.mkdir(parents=True,exist_ok=False)
    last=json.loads((a.client/'build.json').read_text())['map_last_line']
    results=[]
    for line,name in ((last,'late_stop'),(last+1,'stop'),(last,'head'),(last,'both')):
        sub=argparse.Namespace(**vars(a))
        sub.out=a.out/f'line{line}-{name}'
        sub.out.mkdir()
        r=case(sub,906,name,edit_fixture=lambda s,l:gate(s,l,line,'map',beam_pc,1152,last_map_line=last))
        assert r['size']==(1152 if name=='late_stop' else 0)
        if r['grant']:
            assert line <= r['start_line'] <= r['end_line'] < 262
        results.append(dict(line=line, **r))
    # Exercise a late horizontal latch on the last permitted scanline.
    sub=argparse.Namespace(**vars(a))
    sub.out=a.out/'late-horizontal'
    sub.out.mkdir()
    def late(s,labels):
        s=gate(s,labels,last,'map',beam_pc,1152,last_map_line=last)
        s=once(s,'or assert(h)>640','or assert(h)<1000 or h>1150')
        return once(s,'local function loaded()',"""emu.addMemoryCallback(function()
 if not held or index~=held or armed or not tried532 then return end
 local st=emu.getState()
 local f=assert(io.open(ROOT..'/latch616.txt','w'))
 f:write(st.masterClock,',',st['ppu.scanline'],',',st['memoryManager.hClock'] or st['ppu.hClock'])
 f:close()
end,emu.callbackType.read,0x2137)
local function loaded()""")
    r=case(sub,906,'late_stop',edit_fixture=late)
    sample,line,h=map(int,(sub.out/'906-late_stop/latch616.txt').read_text().split(','))
    assert line==last and 1000<=h<1364 and sample<r['grant']
    assert r['size']==1152 and last<=r['start_line']<=r['end_line']<262
    results.append(dict(beam_line=line,beam_h=h,latch_to_last=r['last_write']-sample,**r))
    map_first=a.out/'map-negative-trace'
    prepare(a.trace,map_first,False,map_first=True)
    for g in (906,907):
        for fault in ('missing','duplicate'):
            sub=argparse.Namespace(**vars(a))
            sub.trace=map_first
            sub.out=a.out/f'{g}-{fault}'
            sub.out.mkdir()
            r=case(sub,g,'bad_manifest',edit_fixture=lambda s,l:width(map_fixture(s,l,fault=='duplicate'),1152))
            results.append(dict(fault=fault, **r))
    (a.out/'edges.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('trace','client','mesen','out'):
        p.add_argument('--'+key,type=Path,required=True)
    run(p.parse_args())
