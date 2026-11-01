# SPDX-License-Identifier: MIT
"""Drop the forced legacy loader diagnostic from the trial; retain the live loader and verification."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once, sha
from package_nes_window516 import LABELS

ROOT=Path(__file__).resolve().parents[1]


def prepare(src,out):
    expected=json.loads((ROOT/'analysis/quiet528-verification.json').read_text())
    assert sha(src/'obj-nes-100/firmware.stm')==expected['firmware_SHA256']
    out.mkdir(parents=True,exist_ok=False)
    make=(src/'Makefile').read_text()
    (out/'Makefile').write_text(once(make,'-Wl,--undefined=nes_mcu_load_probe ',''),newline='\n')
    for name in LABELS:
        s=(src/name).read_text()
        assert '516' in s
        (out/name).write_text(s.replace('516','529'),newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    prepare(a.arm,a.out)
