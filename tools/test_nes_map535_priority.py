# SPDX-License-Identifier: MIT
"""Exercise a full four-row DMA and a one-row tail against new head and STOP in both bank states."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once
from test_nes_idle524_priority import case
from test_nes_tile532_edges import width
from test_nes_map526_priority import map_fixture
from test_nes_tile532_priority import prepare


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('trace','client','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    # Directed contention, not timing evidence. Put the actual map packets
    # directly after BEGIN so a pending head tile cannot win the grant.
    trace=a.out/'map-first'
    prepare(a.trace,trace,False,map_first=True)
    a.trace=trace
    results=[]
    for g in (906,907):
        def fixture(s,l):
            s=width(map_fixture(s,l),256)
            # The production selector gives a small head tile priority over
            # an eligible map tail. Arm only when arbitration selects the map.
            length='>=256' if g==906 else '==64'
            s=once(s,'and mapTail() then','and mapTail() and ((word(0x4000+word(0x1252))&0x7000)==0x5000 or word(0x4004+word(0x1252))>160) '
                   +f'and word(0x4004+word(0x1250)-8){length} then')
            return s
        for race in ('head','stop','both','late_head','late_stop','cold'):
            r=case(a,g,race,edit_fixture=fixture)
            assert r['size']==((256 if g==906 else 64) if r['grant'] else 0)
            results.append(r)
    (a.out/'result.json').write_text(json.dumps(results,indent=2)+'\n')
