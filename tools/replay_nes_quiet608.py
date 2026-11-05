"""Trace the idle selector on 957 against the exact measured packet arrivals."""
import argparse
from functools import partial
from pathlib import Path
from unittest.mock import patch

from nes_raw506 import once
from replay_nes_admit556 import frontier, observe, replay
from check_nes_wire600 import read


def focus(source,labels):
    s=observe(source,labels)
    old='local function probe536(event)\n local g=word(0x1226)\n if g~=951 and g~=957 then return end'
    return once(s,old,old.replace('g~=951 and g~=957','g~=957'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('trace','client','mesen','out'):
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.frames=53
    limit=read(a.client/'build.json')['map_chunk_B']
    with patch.object(frontier,'tile_observer',partial(frontier.tile_observer,map_limit=str(limit))),patch.object(replay,'observer',focus):
        replay.run(a)
