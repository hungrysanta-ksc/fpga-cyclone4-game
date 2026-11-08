"""Check actual DMA-return notification, STOP/new-head races and cold recovery."""
import argparse,json
from pathlib import Path
from types import SimpleNamespace
from nes_raw506 import once,sha
from test_nes_tile532_priority import prepare
from test_nes_map526_priority import map_fixture
from test_nes_tile532_edges import width
from test_nes_idle524_priority import case
from test_nes_seal538_stop import exercise


def run(a):
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    source=a.out/'input';prepare(a.trace,source,False,map_first=True)
    rows=[]
    for gen in (906,907):
        sub=SimpleNamespace(trace=source,client=a.client,mesen=a.mesen,out=a.out/f'map{gen}')
        sub.out.mkdir()
        for name in ('head','stop','both','late_head','late_stop','cold','bad_manifest'):
            def edit(s,l):
                s=width(map_fixture(s,l),1152)
                return once(s,'local function activeImage()',
                    '''local notices680=0
emu.addMemoryCallback(function(a,v)
 assert(v==0xa5 and dmaRemaining==0,'notification before DMA return')
 assert(((regs[0x4302]+256*regs[0x4303])&0x7000)==0x5000,'non-map notification')
 notices680=notices680+1
end,emu.callbackType.write,0x601d)
local function activeImage()''')
            rows.append(case(sub,gen,name,edit_fixture=edit))
            print(gen,name,'PASS',flush=True)
    final=a.out/'final';final.mkdir()
    sub=SimpleNamespace(trace=a.trace,client=a.client,mesen=a.mesen,out=final)
    stops=[exercise(sub,g,'final212') for g in (906,907)]
    r=dict(passed=True,client_SHA256=sha(a.client/'sink165.sfc'),map_races=rows,final_ACK_cancel=stops,
        scope='Actual 65816, map data/cursor and retained visible pixels, missing coverage, STOP/head priority and cold restoration. Host event qualification is checked separately in RTL.')
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('trace','client','mesen','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
