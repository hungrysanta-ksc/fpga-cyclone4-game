# SPDX-License-Identifier: MIT
"""Run the established base-only STOP/cleanup harness on the selected MMC ELF."""
import argparse
import sys
from pathlib import Path
from nes_delta231 import ROOT, sha
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--arm",type=Path,required=True)
p.add_argument("--fault",choices=("none","program","done","busy","token"),required=True)
p.add_argument("--out",type=Path,required=True)
p.add_argument("--trial",type=int,help="Use the selected MMC trial's ROM and bitstream paths.")
a=p.parse_args()
obj=a.arm.resolve()/"obj-nes-100"
path=ROOT/"tools/check_nes_nrom464_recovery.py"
s=path.read_text()
s=s.replace("BASE/'probes/nes-nrom418/arm01/src/obj-nes-100'",repr(str(obj)))
s=s.replace("obj="+repr(str(obj)),"obj=Path("+repr(str(obj))+")")
s=s.replace("596a8a73ca2b8a66f946fe612b1f4480ecff258e01b2e9bf32b952e0448cd30c",sha(obj/"firmware.stm"))
# This base-only branch never reads the SD image. The MMC build does not link NROM header/layout.
s=s.replace("'nes_nrom406_header','nes_nrom406_layout',","").replace("rx[1]=0x78","rx[1]=0x7b")
if a.trial is not None:
    for old,new in [('nrom.nes',f'/sd2snes/nes/mmc{a.trial}.nes'),
                    ('/sd2snes/fpga_nrom16.bi3',f'/sd2snes/fpga_mmc{a.trial}.bi3')]:
        literal="b'"+old+"\\0'"
        assert s.count(literal)==1
        s=s.replace(literal,repr(new.encode()+b'\0'))
sys.argv=[str(path),"--fault",a.fault,"--out",str(a.out)]
exec(compile(s,str(path),"exec"),{"__name__":"__main__","__file__":str(path)})
