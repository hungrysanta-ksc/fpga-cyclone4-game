# SPDX-License-Identifier: MIT
import os,shutil
import probe_nes_live317 as observer
from nes_metadata317 import native
from nes_joint317 import apply
from nes_delta231 import ROOT,sha
engine=observer.engine
engine.native=native
previous=engine.prepare
def prepare(*args,**kwargs):
    src,pins=previous(*args,**kwargs);d=args[0]
    if os.environ.get('NES317_ARM_ONLY')!='1':apply(d)
    for n in ('nes_joint317.py','nes_metadata317.py','probe_nes_live317.py','probe_nes_candidate317.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins
engine.prepare=prepare
engine.__file__=__file__
if __name__=='__main__':engine.main()
