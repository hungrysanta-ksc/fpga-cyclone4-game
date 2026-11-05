# SPDX-License-Identifier: MIT
"""Isolate palette head contention using the actual 621 clocked 65816 arrivals."""
import argparse
import json
from functools import partial
from pathlib import Path
from unittest.mock import patch

import observe_nes_repeat545
from analyze_nes_bg620 import csv_groups
from replay_nes_quiet608 import focus, frontier, replay
from test_nes_quiet608 import observe as palette_observer


def run(a):
    a.frames = 53
    rows = csv_groups(a.trace/'window.csv')[957]
    map_dma, = [second for first,second in zip(rows, rows[1:])
                if first['event']=='idle524' and first['value']==65536+2048
                and second['event']=='ppu_dma' and second['value']==1152]
    mark = {}
    measured=getattr(a,'measured',None)
    def palette_pushes(folder):
        pushes=[]
        for line in (folder/'packets.jsonl').read_text().splitlines():
            _,clock,h,_=json.loads(line)
            b=bytes.fromhex(h)
            if int.from_bytes(b[8:10],'little')==957 and b[1]==3:
                pushes.append((int.from_bytes(b[10:12],'little'),clock))
        assert [off for off,_ in pushes]==[0,32,128,360]
        return [clock for _,clock in pushes]
    if measured:
        source=palette_pushes(a.trace)
        changed=palette_pushes(measured)
        measured_delay=(changed[2]-changed[1])-(source[2]-source[1])
    def delay(script):
        path = a.out/'arrivals.tsv'
        lines = []
        for line in path.read_text().splitlines():
            clock, header, payload = line.split('\t')
            if header != 'FINISH':
                h = bytes.fromhex(header)
                if int.from_bytes(h[8:10],'little')==957 and h[1]==3 and int.from_bytes(h[10:12],'little')==128:
                    assert not mark
                    shift=measured_delay if measured else map_dma['clock']+1-int(clock)
                    mark.update(push=int(clock), delay=shift)
                    if measured:
                        assert int(clock)+shift>source[1]
                        mark.update(source_gap=source[2]-source[1],measured_gap=changed[2]-changed[1])
                    else:
                        assert shift>0
            lines.append(f"{int(clock)+mark.get('delay',0)}\t{header}\t{payload}")
        assert mark
        path.write_text('\n'.join(lines)+'\n',newline='\n')
        return script

    def metrics(rows):
        frame = [r for r in rows if r['g']=='957']
        return dict(early=[dict(selector=int(x['value']),B=int(y['value']),line=int(y['line']))
                           for x,y in zip(frame,frame[1:]) if x['event']=='idle524' and y['event']=='ppu_dma'],
                    ACK=int(next(r['clock'] for r in frame if r['op']=='3' and r['event']=='ack')))

    def compare(base, trial):
        cutoff=mark['push']+min(0,mark['delay'])
        prefix = lambda rows: [r for r in rows if int(r['clock']) < cutoff]
        assert prefix(base)==prefix(trial)
        return dict(prefix_events=len(prefix(base)), **mark, baseline=metrics(base), delayed=metrics(trial))

    with patch.object(frontier,'tile_observer',partial(frontier.tile_observer,map_limit='1152')), patch.object(
            replay,'observer',partial(focus,generation=957)), patch.object(observe_nes_repeat545,'observe',palette_observer):
        replay.run(a, edit_script=delay, compare_trace=compare)


if __name__=='__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('client','trace','mesen','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--measured',type=Path,help='Apply only the observed second-to-third PUSH gap difference from this ARM trace.')
    run(p.parse_args())
