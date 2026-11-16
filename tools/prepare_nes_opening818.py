"""Build exact-ROM, no-input MMC3 opening trials from the timed MMC816 code."""
import argparse
from pathlib import Path
import shutil

from prepare_nes_trial802 import PROBES, rename_edition

WORK=PROBES/"nes-opening818"
SRC=PROBES/"nes-trial816/link816/src"
ROM_SHA="ee08f9134ef0e9e3a5f77e4f08244d24739c68d781cb58e2be737916bb3ab5ae"
ADVENTURE_SHA="9d7402da135fd1290346ccc9332836daee3a9a3cda3789999c3f86efdb5b19c2"


def replace_one(b,old,new):
    assert b.count(old)==1,old
    return b.replace(old,new)


def arm(edition):
    dst=WORK/f"patch{edition}"
    title,crc={818:(b"Captain Tsubasa II (J)",b"0xefe35d6fu"),819:(b"Adventure Island IV (J)",b"0xa58fe808u")}[edition]
    rename_edition(SRC,dst,816,edition)
    loader="nes_h1_stm32.c"
    data=replace_one((SRC/loader).read_bytes(),b"header[6]!=0x42",b"header[6]!=0x41")
    (dst/loader).write_bytes(data.replace(b"SMB3(J)",title).replace(b"exact SMB3 CHR-ROM",b"exact trial CHR-ROM"))
    header="nes_mmc479.h"
    (dst/header).write_bytes(replace_one((SRC/header).read_bytes(),b"0x5a04eed7u",crc).replace(b"SMB3(J)",title))


def board(temp):
    base=temp/"nes-trial816-board816"
    dst=temp/"nes-opening818-board"
    dst.mkdir()
    for name in ("rtl","sys"):
        shutil.copytree(base/name,dst/name)
    for f in base.iterdir():
        if f.is_file() and f.suffix in (".sv",".v",".vhd",".qpf",".qsf",".sdc",".hex",".tcl"):
            shutil.copyfile(f,dst/f.name)
    cart=dst/"cart_nrom.sv"
    cart.write_bytes(replace_one(cart.read_bytes(),b".flags(32'd4)",b".flags(32'h00004004)"))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("arm","board"))
    p.add_argument("--temp",type=Path)
    p.add_argument("--edition",type=int,choices=(818,819),default=818)
    a=p.parse_args()
    if a.action=="arm":
        arm(a.edition)
    else:
        board(a.temp)
