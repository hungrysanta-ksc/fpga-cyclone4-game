# SPDX-License-Identifier: MIT
"""Fault the last observed byte or assert STOP one byte earlier on the checked ROM."""
import argparse
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
import trace_nes_owner739 as owner
from nes_raw506 import once


def run(a):
    replay_run=replay.run
    def guarded(args,*,edit_script):
        def edit(s):
            s=edit_script(s)
            s=once(s,'if pw(8)==957 and pb(0)==9 then stop739=true end','')
            anchor='  local seen=v'
            act='seen=v~1' if a.fault=='data' else 'err762=true'
            s=once(s,anchor,anchor+f'\n  if i=={1535 if a.fault=="data" else 1534} and word(0x1226)==957 then {act};stop739=true end')
            return s
        return replay_run(args,edit_script=edit)
    a.mode='stop'
    with patch.object(replay,'run',guarded):
        owner.run(a)
    import csv
    def rows(name):
        return list(csv.DictReader((a.out/name).open()))
    last=[r for r in rows('wire762.csv') if r['g']=='957']
    assert len(last)==1538 and last[-1]['event']=='read' and last[-1]['byte']=='0'
    assert not any(r['g']=='957' and (r['event']=='reveal' or (r['event']=='ack' and r['op']=='3'))
                   for r in rows('window.csv'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('trace','client','mesen','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--fault',choices=('data','stop'),required=True)
    run(p.parse_args())
