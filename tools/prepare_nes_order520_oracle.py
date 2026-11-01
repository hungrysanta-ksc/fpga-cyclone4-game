# SPDX-License-Identifier: MIT
"""Derive the permitted wire order from the original accepted transaction lengths."""
import argparse
import json
import struct
from collections import defaultdict
from itertools import groupby
from pathlib import Path

from check_nes_game478 import sha
from test_nes_raw506_joint import wire_plan


def prepare(a):
    original=json.loads((a.baseline/"joint.json").read_text())
    saved=json.loads((Path(__file__).resolve().parents[1]/"analysis/dense519-verification.json").read_text())
    assert sha(a.baseline/"events.json")==saved["variants"]["baseline"]["pins"]["events.json"]
    assert original["commits"]==53 and original["passed"]
    lengths=defaultdict(list)
    for e in json.loads((a.baseline/"events.json").read_text()):
        if e["event"]=="SPI" and e["opcode"]=="0xe9":
            lengths[e["generation"]].append(e["bytes"]-8)
    a.out.mkdir(parents=True,exist_ok=False)
    def sortable(item):
        q=bytes.fromhex(item[1])
        return q[6]==1 and (not a.compact or wire_plan(q)[0]==0x81)

    for g in range(905,958):
        source=json.loads((a.plans/f"frame{g}/plans.json").read_text())
        end=struct.pack("<HHHBB",g,0,0,3,0)+bytes(16)+b"\xff"*16
        records=source+[[None,end.hex()]]
        pos=0
        expected=[]
        for length in lengths[g]:
            start=pos
            used=0
            while used<length:
                used+=len(wire_plan(bytes.fromhex(records[pos][1])))
                pos+=1
            assert used==length
            for is_obj,run in groupby(records[start:pos],sortable):
                items=list(run)
                if is_obj:
                    assert len({bank for bank,_ in items})==1
                    items.sort(key=lambda x:int.from_bytes(bytes.fromhex(x[1])[2:4],"little"))
                expected.extend(items)
        assert pos==len(records) and expected[-1]==records[-1]
        folder=a.out/f"frame{g}"
        folder.mkdir()
        (folder/"plans.json").write_text(json.dumps(expected[:-1])+"\n",newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("baseline","plans","out"):
        p.add_argument("--"+n,type=Path,required=True)
    p.add_argument("--compact",action="store_true")
    prepare(p.parse_args())
