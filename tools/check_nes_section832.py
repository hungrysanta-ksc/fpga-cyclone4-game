"""Inject a bad HDMA table or missing receipt into the stock 65816 on an early stream."""
import argparse
from pathlib import Path
from types import SimpleNamespace

from prepare_nes_section832 import PROBES
from replay_nes_seal831 import run


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode")
    p.add_argument("fault",choices=("table","coverage","stop"))
    p.add_argument("temp",type=Path)
    p.add_argument("budget",type=Path)
    p.add_argument("--tail",action="store_true")
    a=p.parse_args()
    run(SimpleNamespace(**vars(a),sender="original",phase=1,rom="tail" if a.tail else "stock",after2572=False),
        arm_override=PROBES/"nes-output823"/("link-832"+a.mode),
        tag_override="832"+a.mode+("tail" if a.tail else "")+"-guard-"+a.fault)
