"""Create the four-byte credit variant of the tested generation-sharing receiver."""
import argparse
from pathlib import Path
import shutil

from check_nes_wire600 import ROOT, pin, read
from nes_raw506 import once


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('out',type=Path)
    a=p.parse_args()
    pin(a.source/'src/obj-nes-100/firmware.stm',read(ROOT/'analysis/wire600-verification.json')['ARM']['shared']['firmware_sha256'])
    shutil.copytree(a.source,a.out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    f=a.out/'src/nes_native165.c'
    s=once(f.read_text(),'frame(tx,0xd2,tok,0);if(!fn(ctx,tx,rx,8)||!status(rx))return fail(s,24);',
           'tx[0]=0xd2;tx[1]=tok>>8;tx[2]=tok;tx[3]=crc8(tx,3);if(!fn(ctx,tx,rx,4))return fail(s,24);')
    f.write_bytes(s.encode())
