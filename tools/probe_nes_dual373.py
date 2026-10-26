# SPDX-License-Identifier: MIT
"""Actual unchanged372 ARM on dual-context/ring373 shared RTL."""
import json,shutil
import probe_nes_frontier372 as previous
from nes_dual373 import functional,COMMON
from nes_delta231 import ROOT,sha
engine=previous.engine;old_prepare=engine.prepare

def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0];functional(d)
 for n in COMMON:
  if n not in src:src.append(n)
  pins['shared373/'+n]=sha(d/n)
 for n in ('nes_dual373.py','probe_nes_dual373.py'):shutil.copyfile(ROOT/'tools'/n,d/n)
 (d/'manifest373.json').write_text(json.dumps(dict(shared_boundary={n:sha(d/n) for n in COMMON}),indent=2)+'\n')
 return src,pins
engine.prepare=prepare;engine.__file__=__file__
if __name__=='__main__':engine.main()
