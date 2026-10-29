# SPDX-License-Identifier: MIT
import argparse,sys
from pathlib import Path
from nes_delta231 import ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--arm',required=True,type=Path);p.add_argument('--fault',required=True);p.add_argument('--out',required=True,type=Path);a=p.parse_args();obj=a.arm.resolve()/'obj-nes-100'
s=(ROOT/'tools/check_nes_nrom464_recovery.py').read_text()
s=s.replace("BASE/'probes/nes-nrom418/arm01/src/obj-nes-100'",'Path('+repr(str(obj))+')').replace('596a8a73ca2b8a66f946fe612b1f4480ecff258e01b2e9bf32b952e0448cd30c',sha(obj/'firmware.stm'))
sys.argv=['check_nes_nrom464_recovery.py','--fault',a.fault,'--out',str(a.out)]
exec(compile(s,str(ROOT/'tools/check_nes_nrom464_recovery.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/check_nes_nrom464_recovery.py')})
