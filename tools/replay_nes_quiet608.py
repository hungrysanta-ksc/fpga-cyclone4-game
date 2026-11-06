"""Trace the idle selector for one generation against its measured packet arrivals."""
import argparse
from functools import partial
from pathlib import Path
from unittest.mock import patch

from nes_raw506 import once
import observe_nes_repeat545
from test_nes_quiet608 import observe as palette_observer
from replay_nes_admit556 import frontier, observe, replay
from check_nes_wire600 import read


def focus(source,labels, generation=957):
    s=observe(source,labels)
    old='local function probe536(event)\n local g=word(0x1226)\n if g~=951 and g~=957 then return end'
    return once(s,old,old.replace('g~=951 and g~=957',f'g~={generation}'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('trace','client','mesen','out'):
        p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--generation',type=int,default=957)
    a=p.parse_args();a.frames=53
    limit=read(a.client/'build.json')['map_chunk_B']
    with patch.object(frontier,'tile_observer',partial(frontier.tile_observer,map_limit=str(limit))),patch.object(replay,'observer',partial(focus,generation=a.generation)):
        if 'uniform608' in read(a.client/'labels.json'):
            with patch.object(observe_nes_repeat545,'observe',palette_observer):
                replay.run(a)
        else:
            replay.run(a)
