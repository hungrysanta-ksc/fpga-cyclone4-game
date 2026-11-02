# SPDX-License-Identifier: MIT
"""Create same-width trial labels from the selected and verified ARM image."""
import argparse
from pathlib import Path
from package_nes_window516 import ROOT, read, sha, LABELS

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--trial',type=int,choices=(540,551),default=540)
    a=p.parse_args()
    if a.trial==551:
        selected=read(ROOT/'analysis/upload550-verification.json')
        assert selected['gate']
        previous='540'
        digest=selected['ARM_SHA256']
    else:
        selected=read(ROOT/'analysis/first539-verification.json')
        assert selected['gate']['row']
        previous='533'
        digest=selected['phases'][0]['row']['ARM_SHA256']
    assert sha(a.arm/'obj-nes-100/firmware.stm')==digest
    a.out.mkdir(parents=True,exist_ok=False)
    for name in LABELS:
        source=(a.arm/name).read_text()
        assert previous in source
        (a.out/name).write_text(source.replace(previous,str(a.trial)),newline='\n')
