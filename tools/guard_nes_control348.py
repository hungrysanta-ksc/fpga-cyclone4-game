# SPDX-License-Identifier: MIT
import inspect
from pathlib import Path
original=inspect.getsource
def source(fn):
 s=original(fn)
 s=s.replace('dut.flow.state==dut.flow.EXPAND325','dut.flow.state==dut.flow.ISSUE346&&dut.flow.repeat325&&!dut.flow.prelude_mode&&!dut.flow.meta346')
 s=s.replace('dut.flow.MISSUE313','dut.flow.ISSUE346')
 return s
inspect.getsource=source
if __name__=='__main__':
 import guard_nes_execute332 as base
 base.base.old.CASES.update({29:'E1 shared transaction length mismatch'})
 prior=base.base.old.once
 def inject(s,a,b):
  if a=='endmodule':
   b=b.replace('begin #(NEG319==10?200000000:100000);', 'begin #(NEG319==10?200000000:NEG319==29?1000000:100000);')
   b=b.replace('  disable fork;\n  repeat(8)', '  disable fork;\n  if(NEG319==29&&!spi_front270.ss[1])$fatal(1,"length fault before transaction end348");\n  repeat(8)')
   b=b.replace('  else $fatal(1,"unknown guard319");','  else if(NEG319==29)wait(spi_front270.command==8\'he1&&spi_front270.count==15);\n  else $fatal(1,"unknown guard319");')
   b=b.replace('  else if(NEG319==9)begin',"  else if(NEG319==29)begin force spi_front270.request_length280=16'hffff;end\n  else if(NEG319==9)begin")
  return prior(s,a,b)
 base.base.old.once=inject
 p=Path(__file__).with_name('guard_nes_read336.py');s=p.read_text().replace("'probe_nes_read336.py'","'probe_nes_control348.py'")
 exec(compile(s,str(p),'exec'),dict(__name__='__main__',__file__=__file__))
