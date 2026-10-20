# SPDX-License-Identifier: MIT
"""Split ARM commands on the retained270 queue/core with new65816 traces.

The same packet descriptor still drives SNES reads/DMA and FPGA receipts.
The273 reference programs are checked offline and are NOT transmitted here.
"""
import inspect,shutil
from pathlib import Path
import probe_nes_refill270 as prior
import probe_nes_refill267 as old
from probe_nes_split274 import build,verify
from nes_delta231 import ROOT,sha,once
ORIGINAL_CPU_TRACE=old.cpu_trace

def cpu_trace(d,trace,s,pins,last):
 # Number changed because actual ARM literal splits create additional CPU
 # commands. Do not fake the old trace's header/length/timing.
 ns=dict(old.__dict__)
 code=once(inspect.getsource(ORIGINAL_CPU_TRACE),"r['CPU']['commands']==522","r['CPU']['commands']==544")
 exec(compile(code,'cpu274-trace','exec'),ns)
 return ns['cpu_trace'](d,trace,s,pins,last)

def prepare(*args,**kwargs):
 # prior269 preparation refers to old.prepare; temporarily bind only that
 # function's cpu_trace global, then restore it before further work.
 saved=old.cpu_trace
 try:
  old.cpu_trace=cpu_trace
  src,pins=prior.prepare(*args,**kwargs)
 finally:old.cpu_trace=saved
 d=args[0]
 for name in ['nes_split274.py','nes_split274.inc','probe_nes_split274.py','probe_nes_refill274.py']:
  shutil.copyfile(ROOT/'tools'/name,d/name);pins[name]=sha(ROOT/'tools'/name)
 return src,pins

def worker(*args,**kwargs):
 ns=dict(old.__dict__);ns.update(verify=verify)
 exec(compile(inspect.getsource(old.worker),'worker274','exec'),ns)
 return ns['worker'](*args,**kwargs)

def main():
 ns=dict(old.__dict__);ns.update(prepare=prepare,build=build,worker=worker,__file__=__file__,__doc__=__doc__)
 exec(compile(inspect.getsource(old.main),'refill274-main','exec'),ns);ns['main']()

if __name__=='__main__':main()
