# SPDX-License-Identifier: MIT
"""Replace the complete epoch crossing on the selected 572 START board."""
import argparse
from pathlib import Path
from prepare_nes_start572 import prepare as start572


def prepare(base,out):
    start572(base,out,'loader')
    source=Path(__file__).resolve().parents[1]/'rtl/nes_source_epoch574.sv'
    (out/'nes_source_epoch207.sv').write_bytes(source.read_bytes())


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--base',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    prepare(a.base,a.out)
