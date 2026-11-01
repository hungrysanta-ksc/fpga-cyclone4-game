# SPDX-License-Identifier: MIT
"""Create same-width MMC540 labels from the selected 539 ARM."""
import argparse
from pathlib import Path
from package_nes_window516 import ROOT, read, sha, LABELS

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    selected=read(ROOT/'analysis/first539-verification.json')
    assert selected['gate']['row']
    assert sha(a.arm/'obj-nes-100/firmware.stm')==selected['phases'][0]['row']['ARM_SHA256']
    a.out.mkdir(parents=True,exist_ok=False)
    for name in LABELS:
        source=(a.arm/name).read_text()
        assert '533' in source
        (a.out/name).write_text(source.replace('533','540'),newline='\n')
