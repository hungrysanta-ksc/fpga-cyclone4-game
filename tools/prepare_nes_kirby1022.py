"""Prepare an isolated Kirby ARM loader link for qualification (not an SD image)."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zlib

from cross_nes1022 import rom_path, ROOT
from prepare_nes_trial802 import rename_edition

WORK = ROOT.parent/"probes/nes-cross1022"
BASE = ROOT.parent/"probes/nes-tail1012-final/link"
LINK = WORK/"link"


def replace(file, replacements):
    data=file.read_bytes()
    for old,new,count in replacements:
        assert data.count(old)==count,(file.name,old,data.count(old))
        data=data.replace(old,new)
    file.write_bytes(data)


def prepare(raw):
    firmware=BASE/"src/obj-nes-100/firmware.stm"
    package=json.loads((ROOT/"analysis/trial1012-package.json").read_text())
    assert hashlib.sha256(firmware.read_bytes()).hexdigest()==package["firmware"]
    shutil.copytree(BASE,LINK)
    dest=WORK/"edition"
    rename_edition(BASE/"src",dest,1012,1022)
    for p in dest.iterdir():
        shutil.copy2(p,LINK/"src"/p.name)
    src=LINK/"src"
    replace(src/"nes_mmc479.h",[(b"0xa58fe808u",f"0x{zlib.crc32(raw):08x}u".encode(),1),
                                (b"0x7b",b"0x7c",1),(b"Adventure Island IV (J)",b"Kirby (J)",1),
                                (b"PRG256KiB/CHR128KiB",b"PRG512KiB/CHR256KiB",1)])
    replace(src/"nes_h1_stm32.c",[(b"header[4]!=16 || header[5]!=16",b"header[4]!=32 || header[5]!=32",1),
                                   (b"header[6]!=0x41",b"header[6]!=0x42",1),
                                   (b"rx[4]&0xf8",b"rx[4]&0xf0",1),(b"0x60000",b"0xc0000",5),
                                   (b"Adventure Island IV (J)",b"Kirby (J)",1)])
    replace(src/"nes_rom_verify.c",[(b"0x60000",b"0xc0000",2)])


def verify(raw,adventure):
    from check_nes_opening818 import admission
    bios=LINK/"src/obj-nes-100/firmware.stm"
    tests={}
    for label,src,image,edition,error in [
        ("mmc1012_kirby",BASE/"src",raw,1012,2),("mmc1022_kirby",LINK/"src",raw,1022,0),
        ("mmc1022_adventure",LINK/"src",adventure,1022,2),
        ("mmc1022_bad_last",LINK/"src",raw[:-1]+bytes([raw[-1]^1]),1022,4)]:
        result=admission(src,image,edition)
        assert result==dict(program=error==0,read_B=16 if error==2 else len(image),error=error),(label,result)
        tests[label]=result
    assert bios.stat().st_size<=212992
    return dict(tests=tests,flash_bytes=bios.stat().st_size)


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action",choices=["prepare","verify"])
    ap.add_argument("rom_dir",type=Path)
    a=ap.parse_args()
    raw=rom_path(a.rom_dir,"kirby").read_bytes()
    if a.action=="prepare":
        prepare(raw)
    else:
        print(json.dumps(verify(raw,rom_path(a.rom_dir,"adventure").read_bytes()),indent=2))
