# SPDX-License-Identifier: MIT
"""Narrow only the optional idle map beam on frame 945. Keep original arrivals, checks and final gate."""
import argparse
import json
from pathlib import Path
from replay_nes_map527 import run
from nes_raw506 import once


def test(a):
    g=945
    a.frames=g-904
    body=(a.client/'body.bin').read_bytes()
    # CMP #233; BCC map_beam_ok; CMP #255; BCS defer. Narrow the second CMP.
    sites=[i for i in range(len(body)-7) if body[i:i+3]==bytes.fromhex('c9e990') and body[i+4:i+7]==bytes.fromhex('c9ffb0')]
    site,=sites
    address=0x2000+site+5
    def edit(s):
        anchor='lastStatus=ack[1];sample516("ack",lastStatus)'
        change=f'''if pb(0)==3 and lastStatus==1 and pw(8)=={g-1} then
   assert(rd({address})==255);emu.write({address},233,emu.memType.snesWorkRam);assert(rd({address})==233)
  end'''
        return once(s,anchor,anchor+'\n  '+change)
    def compare(old,new):
        assert [r for r in old if int(r['g'])<g]==[r for r in new if int(r['g'])<g]
        def summary(trace):
            frame=[r for r in trace if int(r['g'])==g]
            seal=[r for r in frame if r['op']=='3']
            return dict(accepted=[(r['index'],r['op'],r['section'],r['value']) for r in frame if r['event']=='ack'],
                        idle_maps=[int(r['value'])-65536 for r in frame if r['event']=='idle524' and int(r['value'])>=65536],
                        seal_dma=[int(r['value']) for r in seal if r['event']=='ppu_dma'],
                        waits=sum(r['event']=='wait169' for r in seal),
                        decision=next((r['event'] for r in seal if r['event'] in ('borrow516','fresh516')),'credit'),
                        seal_load=int(seal[0]['clock']),ACK=int(seal[-1]['clock']))
        b,c=summary(old),summary(new)
        assert b.pop('accepted')==c.pop('accepted')
        assert len(b['idle_maps'])<=1 and not c['idle_maps']
        return dict(target=g,original=b,narrow=c,prior_events=sum(int(r['g'])<g for r in old),
                    frozen_arrivals=True,patched_WRAM_offset=address)
    run(a,edit_script=edit,compare_trace=compare)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('trace','mesen','client','out'):p.add_argument('--'+n,required=True,type=Path)
    test(p.parse_args())
