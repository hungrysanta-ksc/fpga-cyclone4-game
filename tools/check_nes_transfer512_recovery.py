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
p.add_argument("--game",type=Path,help="Exercise all three file passes up to the real MMC RUN call.")
p.add_argument("--revision",type=lambda s:int(s,0),default=0x7b)
a=p.parse_args()
obj=a.arm.resolve()/"obj-nes-100"
path=ROOT/"tools/check_nes_nrom464_recovery.py"
s=path.read_text()
s=s.replace("BASE/'probes/nes-nrom418/arm01/src/obj-nes-100'",repr(str(obj)))
s=s.replace("obj="+repr(str(obj)),"obj=Path("+repr(str(obj))+")")
s=s.replace("596a8a73ca2b8a66f946fe612b1f4480ecff258e01b2e9bf32b952e0448cd30c",sha(obj/"firmware.stm"))
# This base-only branch never reads the SD image. The MMC build does not link NROM header/layout.
s=s.replace("'nes_nrom406_header','nes_nrom406_layout',","").replace("rx[1]=0x78",f"rx[1]={a.revision}")
if a.trial is not None:
    for old,new in [('nrom.nes',f'/sd2snes/nes/mmc{a.trial}.nes'),
                    ('/sd2snes/fpga_nrom16.bi3',f'/sd2snes/fpga_mmc{a.trial}.bi3')]:
        literal="b'"+old+"\\0'"
        assert s.count(literal)==1
        s=s.replace(literal,repr(new.encode()+b'\0'))
if a.revision==0x7d:
    if a.trial is None:
        s=s.replace('/sd2snes/fpga_nrom16.bi3','/sd2snes/nes-chrram.bi3')
    # The browser selects the physical board ID before the ordinary loader.
    s=s.replace("names=['nes_cf86_fail094'", "names=['nes_board_id','nes_cf86_fail094'")
    s=s.replace("u.reg_write(UC_ARM_REG_SP,stack);", "u.mem_write(symbols['nes_board_id'],bytes([0x7d]));u.reg_write(UC_ARM_REG_SP,stack);")
sys.argv=[str(path),"--fault",a.fault,"--out",str(a.out)]
if a.game:
    assert a.trial and a.fault=='none'
    sys.argv.extend(['--game',str(a.game)])
exec(compile(s,str(path),"exec"),{"__name__":"__main__","__file__":str(path)})
