# SPDX-License-Identifier: MIT
"""Change only the map cap at the preceding final ACK, with MMC533 arrivals and beam phase frozen."""
import argparse
import json
from pathlib import Path
import replay_nes_map527 as replay
from nes_raw506 import once,sha
from test_nes_map526_schedule import observer
from test_nes_tile532 import tile_observer
from test_nes_quiet528 import seal_trace


def test(a):
    g=a.generation
    a.frames=g-904
    baseline=(a.client/'body.bin').read_bytes()
    candidate=(a.candidate_client/'body.bin').read_bytes()
    labels=json.loads((a.client/'labels.json').read_text())
    new_labels=json.loads((a.candidate_client/'labels.json').read_text())
    assert len(baseline)==len(candidate) and all(new_labels[k]==v for k,v in labels.items())
    edits=[(0x2000+i,x,y) for i,(x,y) in enumerate(zip(baseline,candidate)) if x!=y]
    assert edits
    def edit(s):
        s=once(seal_trace(s),'(pw(8)~=952 and pw(8)~=954)',f'pw(8)~={g}')
        anchor='lastStatus=ack[1];sample516("ack",lastStatus)'
        writes='\n'.join(f'assert(rd({i})=={x});emu.write({i},{y},emu.memType.snesWorkRam);assert(rd({i})=={y})' for i,x,y in edits)
        return once(s,anchor,anchor+f'\n  if pb(0)==3 and lastStatus==1 and pw(8)=={g-1} then\n{writes}\n  end')
    def stats(rows):
        current=[r for r in rows if int(r['g'])==g]
        seal=[r for r in current if r['op']=='3']
        previous=[r for r in rows if int(r['g'])==g-1 and r['event']=='reveal']
        assert len(previous)==1
        def event(name):
            value,=[r for r in seal if r['event']==name]
            return value
        final=event('final212')
        dma=[int(r['value']) for r in current if r['op']=='-1' and r['event']=='ppu_dma']
        return dict(ACK=int(event('ack')['clock']),final_line=int(final['line']),
                    waits=sum(r['event']=='wait169' and int(r['clock'])>=int(final['clock']) for r in seal),
                    display_VBlanks=int(event('reveal')['frame'])-int(previous[0]['frame']),idle_DMA_B=dma,
                    SEAL_load=int(event('load')['clock']))
    def compare(old,new):
        assert [r for r in old if int(r['g'])<g]==[r for r in new if int(r['g'])<g]
        def accepted(rows):return [(r['index'],r['op'],r['section'],r['value']) for r in rows if r['event']=='ack']
        assert accepted(old)==accepted(new)
        return dict(g=g,reference=stats(old),candidate=stats(new),candidate_SHA256=sha(a.candidate_client/'sink165.sfc'))
    replay.observer=lambda s,l:tile_observer(observer(s,l),l,f'(word(0x1226)=={g} and 256 or 128)')
    replay.run(a,edit_script=edit,compare_trace=compare)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('client','candidate-client','trace','mesen','out'):p.add_argument('--'+n,required=True,type=Path)
    p.add_argument('--generation',required=True,type=int)
    test(p.parse_args())
