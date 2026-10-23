# SPDX-License-Identifier: MIT
import shutil
import probe_nes_live313 as old
from nes_control314 import apply
from nes_delta231 import ROOT,sha
previous=old.prepare
def prepare(*args,**kwargs):
    src,pins=previous(*args,**kwargs);d=args[0];apply(d)
    for name in ('nes_control314.py','probe_nes_live314.py'):
        shutil.copyfile(ROOT/'tools'/name,d/name);pins[name]=sha(d/name)
    return src,pins
old.old.old.old.prepare=prepare
old.old.old.old.__file__=__file__
if __name__=='__main__':old.old.old.old.main()
