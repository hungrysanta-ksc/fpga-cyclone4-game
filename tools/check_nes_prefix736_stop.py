"""Abort an accepted scroll padding fill, keeping the previous displayed bank."""
import argparse
import json
from pathlib import Path

from check_nes_tail735_stop import inject
from nes_raw506 import once
from test_nes_seal538_stop import exercise


def padding_stop(source, offset):
    return once(inject(source, offset), 'pw(10)<1121 and pw(10)+pw(14)>1121',
                'pw(10)==21 and pw(14)==1100')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('trace', 'client', 'mesen', 'out'):
        p.add_argument(name, type=Path)
    p.add_argument('--generation', type=int, required=True)
    a = p.parse_args()
    a.out = a.out.resolve()
    a.out.mkdir(exist_ok=False)
    results = [exercise(a, a.generation, f'pad{n}', edit_packet_case=lambda s: padding_stop(s, n))
               for n in (64, 1088)]
    (a.out / 'result.json').write_text(json.dumps(results, indent=2) + '\n')
