# SPDX-License-Identifier: MIT
"""Isolate the checked 2496 receipt and prevent a later map from taking the first VBlank."""
import argparse
from pathlib import Path
from types import SimpleNamespace

from replay_nes_tail779 import run


def replay(base, reference, client, mesen, out):
    # Use the measured 781C start of every E1. Holding the next map may
    # delay the suffix; later jobs can never advance past their real supply.
    from analyze_nes_supply781 import measure
    result=measure(base,reference)
    first_end=result["ACK968"]+result["first_blank_end"]*21477272/1000
    def boundary(heads):
        offsets={int.from_bytes(h[10:12],"little"):i for i,h in enumerate(heads) if h[1]==2}
        return offsets[2496],offsets[3072]
    def schedule(heads,tx,events):
        before,after=boundary(heads)
        assert after==before+1
        floor={i:e["start"] for i,e in enumerate(tx)}
        floor[after]=max(floor[after],first_end)
        return after,list(range(len(heads))),tx[after-1]["clock"],floor
    run(SimpleNamespace(trace=base,client=client,mesen=mesen,out=out,floor=True,hold=False,pack=False),
        schedule,boundary)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("temp","client","mesen"):
        p.add_argument(k,type=Path)
    p.add_argument("phase",type=int,choices=(1,2))
    a=p.parse_args()
    replay(a.temp/f"nes-supply781-refill3-p{a.phase}",a.temp/f"nes-range778-763-p{a.phase}",
           a.client,a.mesen,a.temp/f"nes-grant782-hold-p{a.phase}")
