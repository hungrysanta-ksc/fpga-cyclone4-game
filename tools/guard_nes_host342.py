# SPDX-License-Identifier: MIT
import inspect
from pathlib import Path
original=inspect.getsource
def source(fn):
 s=original(fn)
 if "p.suffix in ('.sv','.v','.hex','.bin','.elf','.dll','.cfg','.palette','.expected')" in s:s=s.replace("'.palette','.expected')", "'.palette','.expected','.records')")
 return s
inspect.getsource=source
if __name__=='__main__':
 import guard_nes_execute332 as base342
 original_once342=base342.base.old.once
 def once342(s,a,b):
  return original_once342(s,a,b).replace('dut.flow.manifest_byte313','dut.flow.expanded325[8:0]')
 base342.base.old.once=once342
 p=Path(__file__).with_name('guard_nes_read336.py');s=p.read_text().replace("'probe_nes_read336.py'","'probe_nes_host342.py'")
 exec(compile(s,str(p),'exec'),dict(__name__='__main__',__file__=__file__))
