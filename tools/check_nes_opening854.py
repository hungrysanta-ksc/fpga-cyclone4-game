"""Isolate the measured startup displacement while keeping all 815R handlers byte-identical."""
import argparse
from pathlib import Path
import shutil

from prepare_nes_column854 import PROBES,ROOT
from nes_raw506 import sha


def delay(out,count):
    base=PROBES/'nes-output815/client'
    assert sha(base/'sink165.sfc')=='3ca9aaefd9efad64a3cb63b59b627314f9f6b8e87fb79e236ba7e7d01fa856e1'
    rom=bytearray((base/'sink165.sfc').read_bytes())
    original=bytes.fromhex('5c 00 20 7e')
    at=rom.index(original,0,272)
    pos=5056-24
    routine=bytes.fromhex('08 da a2')+count.to_bytes(2,'little')+bytes.fromhex('ca d0 fd fa 28')+original
    assert rom[pos:pos+len(routine)]==bytes([255])*len(routine)
    rom[pos:pos+len(routine)]=routine
    rom[at:at+4]=bytes((0x5c,))+(0x8000+pos).to_bytes(3,'little')
    out.mkdir()
    for name in ('body.bin','labels.json','build.json'):shutil.copyfile(base/name,out/name)
    (out/'sink165.sfc').write_bytes(rom)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('out',type=Path);p.add_argument('iterations',type=int)
    a=p.parse_args()
    delay(a.out,a.iterations)
