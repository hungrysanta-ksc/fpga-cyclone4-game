# SPDX-License-Identifier: MIT
"""Exact180 runtime with schema3 descriptor and truthful episode log label."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_reject180 import replace

def prepare(prior,out):
    assert sha(prior/'src/obj-nes-100/firmware.stm')=='c9e97fce2a44f2c1995a22cdef0f2d2b1333c4f0e47d8adf05a63af0c1799ea6'
    m=json.loads((prior/'preparation-reject180.json').read_bytes())
    assert not out.exists();out.mkdir(parents=True);r=dict(copied={},changed={},added={})
    for n,h in (m['copied']|m['changed']|m['added']).items():
        assert sha(prior/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((prior/n).read_bytes());r['copied'][n]=h
    for n,a,b in [('src/nes_run136.inc','rx[6]!=96||rx[7]!=2||','rx[6]!=96||rx[7]!=3||'),('src/nes_menu_diagnostic.c','LAST16_REJECT180_V2','LAST16_EPISODE180_V3')]:
        p=out/n;p.write_text(replace(p.read_text(),a,b),encoding='utf8',newline='\n');r['changed'][n]=sha(p)
    r.update(history_schema=3,hardware_package=False,public_sources={n:sha(ROOT/n) for n in ['tools/nes_minreject180_mcu.py','tools/nes_reject180.py']})
    for n in ['preparation-minreject180.json','preparation-runlease165.json']:(out/n).write_text(json.dumps(r,indent=2)+'\n')
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.prior,a.out)
