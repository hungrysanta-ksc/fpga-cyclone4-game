# SPDX-License-Identifier: MIT
"""Fixed-block repeat348 on338 RTL, only decoder change to336 ARM."""
import inspect,shutil
import probe_nes_live340 as live
import probe_nes_joint340 as joint
from nes_fixed348 import source,native
from nes_delta231 import ROOT,sha
joint.apply=source
joint.host=lambda d:None
scope=dict(joint.__dict__)
s=inspect.getsource(joint.prepare).replace('probes/nes-hybrid340/arm03','probes/nes-fixed347/arm01')
exec(compile(s,__file__,'exec'),scope)
live.old_prepare=scope['prepare']
scope2=dict(live.__dict__)
s=inspect.getsource(live.prepare).replace('probes/nes-hybrid340/arm03','probes/nes-fixed347/arm01')
exec(compile(s,__file__,'exec'),scope2)
prepare_old=scope2['prepare']
engine=live.engine

def prepare(*a,**k):
 src,pins=prepare_old(*a,**k);d=a[0]
 for n in ('nes_fixed348.py','probe_nes_fixed348.py','nes_fixed347.py'):
  shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
 return src,pins
engine.prepare=prepare
engine.native=native
engine.__file__=__file__
if __name__=='__main__':engine.main()
