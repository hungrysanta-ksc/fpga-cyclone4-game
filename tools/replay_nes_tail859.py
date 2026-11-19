"""Observe section 5 literal restoration on the linked CPU without changing its schedule."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import replay_nes_column853 as replay
from nes_raw506 import once
from prepare_nes_seal858 import ROOT


def run(temp, clip, phase, tag, arm, client):
    monitor = replay.monitor
    labels = json.loads((client/'labels.json').read_bytes())
    body = (client/'body.bin').read_bytes()
    dma = labels['literal_length227']
    assert body[dma-0x7e2000:dma-0x7e2000+7] == bytes.fromhex('e2 20 a9 01 8d 0b 42')
    points = dict(tail_data=labels['data'], tail_literal=labels['literal1814'],
                  tail_dma=dma+4, tail_after_trigger_PC=dma+7, tail_accepted=labels['accepted'],
                  tail_reply=labels['reply'])

    def observed(template, scene):
        template = monitor(template, scene)
        hooks = [f"checkedMem527(function() if packet and pw(8)==964 and pb(0)==2 and pb(1)==5 then sample516('{name}') end end,emu.callbackType.exec,{address})"
                 for name, address in points.items()]
        return once(template, 'local function loaded()', '\n'.join(hooks)+'\nlocal function loaded()')

    with patch.object(replay, 'monitor', observed):
        replay.run(temp, clip, phase, True, tag+'-on', arm=arm, client=client,
                   budget=Path.home()/'Downloads/nes-budget-mmc855.txt')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp', type=Path)
    parser.add_argument('clip', choices=['opening','demo','transition'])
    parser.add_argument('phase', type=int, choices=[1,2])
    parser.add_argument('tag')
    parser.add_argument('--arm', type=Path, default=ROOT/'link-c/src')
    parser.add_argument('--client', type=Path, default=ROOT/'client-e')
    args = parser.parse_args()
    run(**vars(args))
