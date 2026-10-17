# SPDX-License-Identifier: MIT
"""Recompute full linked221 RUN/IRQ bound, including2816B index and96B bins."""
import check_nes_status220_arm as prior
from nes_index221_arm import instrumentation
from nes_runtime213 import once
s=prior.s.replace('preparation-status220.json','preparation-index221.json')
s=s.replace("BASE/'probes/nes-startup214/check02'", "BASE/'probes/nes-status220/check01'")
s=s.replace("BASE/'probes/nes-startup214/check02-review.json'", "BASE/'probes/nes-status220/check01-review.json'")
s=once(s,"assert (a.arm/'src/nes_native_runtime165.c').read_text()==runtime((BASE/'probes/nes-budget210/arm03/src/nes_native_runtime165.c').read_text())",
       "assert (a.arm/'src/nes_native_runtime165.c').read_text()==instrumentation((BASE/'probes/nes-status220/arm01/src/nes_native_runtime165.c').read_text())")
s=once(s,"cb['nes_resident211_slot']=['resident_plan213']", "cb['nes_resident211_slot']=['resident_plan213']\n cb['resident_plan213']=['native_ticks165']")
for x,y in [('GAME 220','GAME 221'),('game220.nes','game221.nes'),('fpga_n220.bi3','fpga_n221.bi3'),('last-220.txt','last-221.txt'),('nes-progress-220.txt','nes-progress-221.txt'),('nes-budget-220.txt','nes-budget-221.txt'),('NES-GAME220-DEV','NES-GAME221-DEV'),('tools/check_nes_status220_arm.py','tools/check_nes_index221_arm.py')]:s=s.replace(x,y)
ns=dict(prior.ns);ns['__file__']=__file__;ns['instrumentation']=instrumentation;exec(compile(s,'check221','exec'),ns)
if __name__=='__main__':ns['main']()
