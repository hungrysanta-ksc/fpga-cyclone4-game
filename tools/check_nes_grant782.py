# SPDX-License-Identifier: MIT
"""Check linked report bytes, ownership, padding and STOP for each ARM build."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from check_nes_padding733 import run as padding
from check_nes_report594 import Reports
from check_nes_supply781 import check, sealed_wait


def verify(base, arm, out):
    out.mkdir(exist_ok=False)
    guards=check(arm,extra=True,owner=True)
    guards["uncached"]=sealed_wait(arm,"uncached")
    padding(SimpleNamespace(base=base,arm=arm,out=out/"padding.json"))
    old,new=Reports(base),Reports(arm)
    reports=[]
    for persist in (False,True):
        a,original=old.run(persist,763)
        b,candidate=new.run(persist,763)
        assert a==b
        reports.append(dict(persist=persist,budget_bytes=len(b[2])-1,
                            budget=hashlib.sha256(b[2]).hexdigest(),
                            baseline=original,candidate=candidate))
    (out/"guards.json").write_text(json.dumps(dict(guards=guards,reports=reports),indent=2)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("base","arm","out"):
        p.add_argument(k,type=Path)
    a=p.parse_args()
    verify(a.base,a.arm,a.out)
