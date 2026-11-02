# SPDX-License-Identifier: MIT
"""Capture every 952 ROM grant and validate the ARM batch against original planner records."""
import argparse
from itertools import groupby
import json
from pathlib import Path
from test_nes_tile532 import joint, OutputRuntime, CheckedLink, run_schedule, tile_observer, instrument
from test_nes_raw506_joint import wire_plan


class SupplyLink(CheckedLink):
    def accept(self, tx, t):
        if tx[0] == 0xe9:
            # Only the compact OBJ suffix can be reordered within an E9.
            # The parent independently compares every encoded byte and consumes END.
            plans = self.plansets[self.generation]
            start, stop = self.plan_at, min(len(plans),self.plan_at+tx[3])
            if self.a.keep_run and 1<=tx[3]<=7:
                # Encoder sorts up to 15 original compact records before
                # it divides a sparse prefix from the adjacent suffix.
                group=plans[start:start+15]
                if len(group)==15 and all(wire_plan(q)[0]==0x81 for q in group):
                    group=sorted(group,key=lambda q:q[2])
                    cut=14
                    while cut and group[cut][2]==group[cut-1][2]+1:
                        cut-=1
                    if cut==tx[3]:
                        plans[start:start+15]=group
            ordered=[]
            for compact, run in groupby(plans[start:stop], lambda q:wire_plan(q)[0]==0x81):
                records=list(run)
                if compact:
                    records.sort(key=lambda q:int.from_bytes(q[2:4],'little'))
                ordered.extend(records)
            plans[start:stop]=ordered
        return super().accept(tx,t)

    def next_rom(self, request):
        g, kind=self.owners[0]
        response=super().next_rom(request)
        if g==952:
            self.phases[g].setdefault('rom_service',[]).append([kind, request,self.allocations[-1]['grant'],response])
        return response


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('arm','data','fixture','plans','client','mesen','out','calendar','driver503','capture'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--start-clock',type=int,required=True)
    p.add_argument('--keep-run',action='store_true')
    a=p.parse_args()
    a.map526=a.trace_rom=a.trace_credit=True
    joint.Runtime=OutputRuntime
    labels=json.loads((a.client/'labels.json').read_text())
    limit=json.loads((a.client/'build.json').read_text())['map_chunk_B']
    run_schedule(a,lambda s,args:tile_observer(instrument(s,args),labels,str(limit)),SupplyLink,frames=53)
