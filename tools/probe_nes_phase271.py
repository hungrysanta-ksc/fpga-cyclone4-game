# SPDX-License-Identifier: MIT
"""Reproduce candidate A: only tile-ready backoff, with unchanged270 SPI RTL."""
import inspect,shutil
import probe_nes_refill267 as old
import probe_nes_refill270 as prior
from probe_nes_refill271 import worker
from nes_delta231 import ROOT,sha

def prepare(*args,**kwargs):
 d=args[0];src,pins=prior.prepare(*args,**kwargs)
 for n in ['nes_output271_phase.c','probe_nes_phase271.py','probe_nes_refill271.py']:
  shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(ROOT/'tools'/n)
 return src,pins

def build(d):
 prior.build(d)
 (d/'nes_output264.c').write_bytes((ROOT/'tools/nes_output271_phase.c').read_bytes())

def main():
 ns=dict(old.__dict__);ns.update(prepare=prepare,build=build,worker=worker,__file__=__file__,__doc__=__doc__)
 exec(compile(inspect.getsource(old.main),'phase271-main','exec'),ns);ns['main']()

if __name__=='__main__':main()
