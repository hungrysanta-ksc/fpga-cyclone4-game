# SPDX-License-Identifier: MIT
import shutil
import probe_nes_query356 as previous
from nes_cancel358 import apply
from nes_delta231 import ROOT,sha
engine=previous.engine
old_prepare=engine.prepare
def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0];apply(d)
 for n in ('nes_cancel358.py','probe_nes_cancel358.py'):
  shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
 return src,pins
engine.prepare=prepare
engine.__file__=__file__
if __name__=='__main__':engine.main()
