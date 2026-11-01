# SPDX-License-Identifier: MIT
"""Release a mixed BG/OBJ batch before one producer drain monopolizes the next ROM window."""
import argparse
import json
from itertools import groupby
from pathlib import Path
from nes_raw506 import once
from test_nes_raw506_joint import wire_plan
from run_nes_scroll229 import sha


def wire(item):
    return wire_plan(bytes.fromhex(item[1]))


def expected(records):
    batch, output = [], []
    first_bg = True

    def flush():
        for compact, run in groupby(batch, key=lambda item: wire(item)[0] == 0x81):
            items = list(run)
            if compact:
                assert len({bank for bank, _ in items}) == 1
                items.sort(key=lambda item: wire(item)[3])
            output.extend(items)
        batch.clear()

    for item in records:
        q = wire(item)
        if (len(batch) == 8 and q[0] == 0x81 and any(wire(p)[0] != 0x81 for p in batch)
                or sum(len(wire(p)) for p in batch) + len(q) > 240):
            flush()
        batch.append(item)
        if first_bg and bytes.fromhex(item[1])[6] == 0:
            flush()
            first_bg = False
        if len(batch) == 15:
            flush()
    flush()
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('arm','plans','patch','oracle'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    baseline = json.loads((Path(__file__).resolve().parents[1]/'analysis/frontier536-verification.json').read_text())
    assert sha(args.arm/'obj-nes-100/firmware.stm') == baseline['phases'][0]['base']['firmware']
    args.patch.mkdir(parents=True,exist_ok=False)
    args.oracle.mkdir(parents=True,exist_ok=False)
    name = 'nes_plan_service200.c'
    source = once((args.arm/name).read_text(),'p->count==15||p->bytes+n>240',
                  '(p->count==8 && p->obj_start && encoded[0]==0x81)||p->count==15||p->bytes+n>240')
    (args.patch/name).write_text(source,newline='\n')
    for generation in range(905,958):
        rel = Path(f'frame{generation}')/'plans.json'
        records = json.loads((args.plans/rel).read_text())
        ordered = expected(records)
        assert sorted(ordered) == sorted(records)
        (args.oracle/rel.parent).mkdir()
        (args.oracle/rel).write_text(json.dumps(ordered)+'\n')
