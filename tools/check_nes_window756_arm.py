# SPDX-License-Identifier: MIT
"""Check the narrowed right-page history on the linked ARM, including fallback."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import check_nes_group628_arm as original
from check_nes_credit752 import verify


def run(src,out,delta):
    guards=verify(src,'mapobj')
    if delta:
        original.run(SimpleNamespace(src=src,out=out),capacity=700,end=3584)
        guards['map_delta']=json.loads(out.read_text())
    out.write_text(json.dumps(guards,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('src','out'):p.add_argument(name,type=Path)
    p.add_argument('--delta',action='store_true')
    a=p.parse_args()
    run(a.src,a.out,a.delta)
