# SPDX-License-Identifier: MIT
import os,shutil
import probe_nes_completion331 as previous
from nes_execute332 import native,apply
from nes_delta231 import ROOT,sha
engine=previous.engine
old_prepare=engine.prepare


def prepare(*args,**kwargs):
    src,pins=old_prepare(*args,**kwargs);d=args[0]
    if os.environ.get('NES332_ARM_ONLY')!='1':apply(d)
    for n in ('nes_execute332.py','probe_nes_execute332.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins


old_init=engine.ARM296.__init__
def observed_init(self,*args,**kwargs):
    old_init(self,*args,**kwargs)
    for name in ('publish_map332','oam227','span','dirty_span231'):
        if name in self.symbols:self.watch317[self.symbols[name]&~1]=name
engine.ARM296.__init__=observed_init
engine.prepare=prepare
engine.native=native
engine.__file__=__file__
if __name__=='__main__':engine.main()
