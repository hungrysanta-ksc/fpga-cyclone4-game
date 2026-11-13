"""Observe only673's declared payload fields, excluding unused video metadata.

Actual target/IRQ/clock policy unchanged. Require original baseline equivalence.
"""
import runpy
from pathlib import Path
from unittest.mock import patch
from nes_raw506 import once

original=runpy.run_module
def execute(name,*args,**kwargs):
 if name!='test_nes_ready673':return original(name,*args,**kwargs)
 path=Path(__file__).with_name(name+'.py');s=path.read_text()
 s=once(s,"        cpu.u.hook_add(UC_HOOK_MEM_WRITE,writes,begin=cpu.video,end=cpu.video+layout['size']-1)",
  "        for address,length in ranges.values():\n            cpu.u.hook_add(UC_HOOK_MEM_WRITE,writes,begin=address,end=address+length-1)")
 exec(compile(s,str(path),'exec'),dict(__file__=str(path),__name__='__main__'))

if __name__=='__main__':
 with patch.object(runpy,'run_module',execute):runpy.run_module('test_nes_lazy716',run_name='__main__')
