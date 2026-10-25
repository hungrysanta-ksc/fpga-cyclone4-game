# SPDX-License-Identifier: MIT
import os
import shutil
os.environ['NES328_ARM_ONLY']='1'
import probe_nes_joint328 as previous
from nes_resume330 import native
from nes_delta231 import ROOT,sha
engine=previous.engine
old_prepare=engine.prepare

def prepare(*args,**kwargs):
    src,pins=old_prepare(*args,**kwargs);d=args[0]
    for n in ('nes_resume330.py','probe_nes_resume330.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins

old_init=engine.ARM296.__init__
def observed_init(self,*args,**kwargs):
    old_init(self,*args,**kwargs)
    for name in ('prepare_map330','take_map330','map247','bulk289'):
        if name in self.symbols:self.watch317[self.symbols[name]&~1]=name
engine.ARM296.__init__=observed_init
engine.prepare=prepare
engine.native=native
engine.__file__=__file__
if __name__=='__main__':engine.main()
