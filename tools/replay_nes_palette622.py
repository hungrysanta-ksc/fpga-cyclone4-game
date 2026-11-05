# SPDX-License-Identifier: MIT
"""Isolate palette head contention using the actual 621 clocked 65816 arrivals."""
import argparse
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
    def delay(script):
        path = a.out/'arrivals.tsv'
        lines = []
        for line in path.read_text().splitlines():
            clock, header, payload = line.split('\t')
            if header != 'FINISH':
                h = bytes.fromhex(header)
                if int.from_bytes(h[8:10],'little')==957 and h[1]==3 and int.from_bytes(h[10:12],'little')==128:
                    assert not mark
                    mark.update(push=int(clock), delay=map_dma['clock']+1-int(clock))
                    assert mark['delay'] > 0
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
        prefix = lambda rows: [r for r in rows if int(r['clock']) < mark['push']]
        assert prefix(base)==prefix(trial)
        return dict(prefix_events=len(prefix(base)), **mark, baseline=metrics(base), delayed=metrics(trial))

    with patch.object(frontier,'tile_observer',partial(frontier.tile_observer,map_limit='1152')), patch.object(
            replay,'observer',partial(focus,generation=957)), patch.object(observe_nes_repeat545,'observe',palette_observer):
        replay.run(a, edit_script=delay, compare_trace=compare)


if __name__=='__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('client','trace','mesen','out'):
        p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())
