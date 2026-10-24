# SPDX-License-Identifier: MIT
import inspect
from pathlib import Path
original_source=inspect.getsource
def source(fn):
 s=original_source(fn)
 if "p.suffix in ('.sv','.v','.hex','.bin','.elf','.dll','.cfg','.palette','.expected')" in s:s=s.replace("'.palette','.expected')", "'.palette','.expected','.records')")
 return s
inspect.getsource=source
if __name__=='__main__':
 import guard_nes_execute332 as base
 base.base.old.CASES.update({24:'STOP during contiguous record build',25:'STOP during deferred MASK RAM write'})
 prior=base.base.old.once
 def once344(s,a,b):
  if a=='endmodule':
   b=b.replace('endmodule', '''always @(posedge clk)if(!reset&&!source_fault)begin
 if(dut.core.encoder.state==dut.core.encoder.BUILD344&&dut.core.encoder.mask_pending278)$fatal(1,"record build versus deferred mask collision344");
 if(dut.core.encoder.ram_a_we&&(dut.core.encoder.state==dut.core.encoder.BUILD344||dut.core.encoder.state==dut.core.encoder.FSTORE||dut.core.encoder.mask_pending278)&&(dut.core.encoder.ram_a_addr<768||dut.core.encoder.ram_a_addr>=844))$fatal(1,"record range344");
end
endmodule''')
   b=b.replace('  else $fatal(1,"unknown guard319");','  else if(NEG319==24)wait(dut.core.encoder.state==dut.core.encoder.BUILD344);\n  else if(NEG319==25)wait(dut.core.encoder.mask_pending278);\n  else $fatal(1,"unknown guard319");')
   b=b.replace('if(NEG319<=4||','if(NEG319==24||NEG319==25||NEG319<=4||')
  return prior(s,a,b)
 base.base.old.once=once344
 p=Path(__file__).with_name('guard_nes_read336.py');s=p.read_text().replace("'probe_nes_read336.py'","'probe_nes_record344.py'")
 exec(compile(s,str(p),'exec'),dict(__name__='__main__',__file__=__file__))
