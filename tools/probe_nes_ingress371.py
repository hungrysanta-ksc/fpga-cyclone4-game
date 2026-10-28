# SPDX-License-Identifier: MIT
"""Bind real M4 early storage release to the canonical hint/plan handoff RTL."""
import json,shutil,sys
rx_only='--rx-only' in sys.argv
if rx_only:sys.argv.remove('--rx-only')
import probe_nes_lookup370 as previous
from nes_ingress371 import materialize,COMMON,arm
from nes_source368 import compile_arm
from nes_delta231 import ROOT,sha
engine=previous.engine;old_prepare=engine.prepare;old_build=engine.build_rom
def prepare(*args,**kwargs):
 src,pins=old_prepare(*args,**kwargs);d=args[0];materialize(d)
 if rx_only:
  for n in ('nes_source_tile192.sv','nes_chr_cache192.sv','nes_plan_path267.sv'):
   shutil.copyfile(ROOT.parent/'probes/nes-source368/map01'/n,d/n)
 for n in COMMON:
  if n not in src:src.append(n)
  pins['shared371/'+n]=sha(d/n)
 for n in ('nes_ingress371.py','nes_receive371.c','probe_nes_ingress371.py'):shutil.copyfile(ROOT/'tools'/n,d/n)
 (d/'manifest371.json').write_text(json.dumps(dict(rx_only=rx_only,shared_boundary={n:sha(d/n) for n in COMMON}),indent=2)+'\n')
 return src,pins
def build(d):
 old_build(d);shutil.copyfile(d/'output.elf',d/'pre371-output.elf');arm(d);compile_arm(d)
engine.prepare=prepare;engine.build_rom=build;engine.__file__=__file__
if __name__=='__main__':engine.main()
