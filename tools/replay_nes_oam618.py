# SPDX-License-Identifier: MIT
"""Hold arrivals fixed through the first OAM PUSH and move the complete suffix together."""
import argparse
import json
from functools import partial
from pathlib import Path
from unittest.mock import patch
import observe_nes_repeat545
from replay_nes_quiet608 import focus,frontier,replay
from test_nes_quiet608 import observe as palette_observer
from nes_raw506 import once


def checked_control(a):
    labels=json.loads((a.client/'labels.json').read_text())
    body=(a.client/'body.bin').read_bytes()
    branch=body.index(bytes.fromhex('ad2410f0'),labels['group538']-0x7e2000)+3
    assert branch<labels['sample618']-0x7e2000
    def disable(source):
        return once(source,'local function loaded()',f"""emu.addMemoryCallback(function()
 if word(0x1226)==954 then
  assert(rd({branch+0x2000})==0xf0)
  emu.write({branch+0x2000},0x80,emu.memType.snesWorkRam)
 end
end,emu.callbackType.exec,{labels['upload165_entry']})
local function loaded()""")
    def compare(on,off):
        def portion(rows):
            i=next(i for i,r in enumerate(rows) if r['g']=='954' and r['event']=='upload165_entry')
            return rows[:i+1],rows[i+1:]
        prefix,after=portion(on)
        same,control=portion(off)
        assert prefix==same
        def summary(rows):
            early=[]
            for r in rows:
                if r['event'] in ('final212','wait169'):break
                if r['event']=='ppu_dma':early.append([int(r['line']),int(r['value'])])
            ack,=[r for r in rows if r['g']=='954' and r['op']=='3' and r['event']=='ack']
            return dict(early=early,ack=int(ack['clock']))
        return dict(prefix_events=len(prefix),enabled=summary(after),disabled=summary(control))
    a.frames=50
    with patch.object(frontier,'tile_observer',partial(frontier.tile_observer,map_limit='1152')),patch.object(
            replay,'observer',partial(focus,generation=954)),patch.object(observe_nes_repeat545,'observe',palette_observer):
        replay.run(a,edit_script=disable,compare_trace=compare)


def run(a):
    a.frames=51
    def shift(script):
        path=a.out/'arrivals.tsv'
        rows=[]
        delayed=False
        for line in path.read_text().splitlines():
            t,body,payload=line.split('\t')
            if body!='FINISH':
                b=bytes.fromhex(body)
                if int.from_bytes(b[8:10],'little')==955 and b[1]==4:
                    delayed=True
            rows.append(f'{int(t)+(5500 if delayed else 0)}\t{body}\t{payload}')
        assert delayed
        path.write_text('\n'.join(rows)+'\n',newline='\n')
        return script
    def compare(base,new):
        def prefix(rows):
            i=next(i for i,r in enumerate(rows) if r['g']=='955' and r['event']=='ppu_dma' and r['value']=='1152')
            end=next(j for j in range(i+1,len(rows)) if rows[j]['event']=='ppu_last')
            return rows[:end+1]
        # DMA can change before the original OAM load once the delayed head is absent.
        def summary(rows):
            r=[x for x in rows if x['g']=='955']
            grants=[(int(y['line']),int(x['value'])-65536,int(y['value'])) for x,y in zip(r,r[1:])
                    if x['event']=='idle524' and int(x['value'])>=65536 and y['event']=='ppu_dma']
            return dict(grants=grants,ACK=int(next(x['clock'] for x in r if x['op']=='3' and x['event']=='ack')))
        assert [x for x in base if int(x['g'])<955]==[x for x in new if int(x['g'])<955]
        assert prefix(base)==prefix(new)
        return dict(shift_clocks=5500,base=summary(base),delayed=summary(new))
    with patch.object(frontier,'tile_observer',partial(frontier.tile_observer,map_limit='1152')),patch.object(
            replay,'observer',partial(focus,generation=955)),patch.object(observe_nes_repeat545,'observe',palette_observer):
        replay.run(a,edit_script=shift,compare_trace=compare)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('client','trace','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--skip-checked',action='store_true')
    a=p.parse_args()
    if a.skip_checked:checked_control(a)
    else:run(a)
