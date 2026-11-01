# SPDX-License-Identifier: MIT
"""Exclude the first/last five seconds from future display-completion counters."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once, sha

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a = p.parse_args()
    selected = json.loads((ROOT/'analysis/trial540-package.json').read_text())
    assert sha(a.arm/'obj-nes-100/firmware.stm') == selected['firmware_SHA256']
    source = (a.arm/'nes_budget210.c').read_text()
    source = once(source,'if(elapsed>=100 && elapsed<6000)', 'if(elapsed>=500 && elapsed<5500)')
    source = once(source,'display_1_40_60=', 'display_5_40_55=')
    a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'nes_budget210.c').write_text(source,encoding='utf8',newline='\n')
