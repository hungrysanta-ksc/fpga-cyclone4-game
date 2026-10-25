# SPDX-License-Identifier: MIT
import os,shutil
import probe_nes_resume330 as previous
from nes_completion331 import native,apply
from nes_delta231 import ROOT,sha
engine=previous.engine
old_prepare=engine.prepare


def prepare(*args,**kwargs):
    src,pins=old_prepare(*args,**kwargs);d=args[0]
    if os.environ.get('NES331_ARM_ONLY')!='1':apply(d)
    for n in ('nes_completion331.py','probe_nes_completion331.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins


engine.prepare=prepare
engine.native=native
engine.__file__=__file__
if __name__=='__main__':engine.main()
