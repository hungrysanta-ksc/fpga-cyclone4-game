"""Relabel selected 664-all ARM for the 665 board/65816 hardware trial."""
import argparse
import shutil
from pathlib import Path
from check_nes_fault641 import digest, evidence
from package_nes_window516 import LABELS


def prepare(base,out):
    assert digest(base/'src/obj-nes-100/firmware.stm')==evidence('entry665-verification.json')['ARM_SHA256']
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log','*.json','base-*'))
    for name in LABELS:
        p=out/'src'/name
        data=p.read_bytes()
        assert b'662' in data and b'666' not in data
        p.write_bytes(data.replace(b'662',b'666'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();prepare(a.base,a.out)
