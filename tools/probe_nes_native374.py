# SPDX-License-Identifier: MIT
"""Unchanged372 ARM+dual373 with native-word plan execution374."""
import json,shutil
import probe_nes_dual373 as previous
from nes_native374 import materialize,COMMON
from nes_delta231 import ROOT,sha
engine=previous.engine;old_prepare=engine.prepare
def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0];materialize(d)
 pins['shared374/nes_plan_batch206.sv']=sha(d/'nes_plan_batch206.sv')
 for n in ('nes_native374.py','probe_nes_native374.py'):shutil.copyfile(ROOT/'tools'/n,d/n)
 (d/'manifest374.json').write_text(json.dumps(dict(shared_boundary={n:sha(d/n) for n in COMMON}),indent=2)+'\n')
 return src,pins
import probe_nes_refill267 as run_owner374
old_run374=run_owner374.run
def run374(tool,args,*a,**k):
 if str(tool).lower().endswith('vsim.exe'):args=['-L','altera_mf_ver',*args]
 return old_run374(tool,args,*a,**k)
run_owner374.run=run374
engine.prepare=prepare;engine.__file__=__file__
if __name__=='__main__':engine.main()
