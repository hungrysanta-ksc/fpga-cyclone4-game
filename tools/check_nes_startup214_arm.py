# SPDX-License-Identifier: MIT
"""Reuse213 linked RUN/IRQ proof with unchanged runtime and24B boot evidence."""
import inspect
import check_nes_runtime213_arm as prior
from nes_runtime213 import once
s=inspect.getsource(prior.main)
s=s.replace('preparation-runtime213.json','preparation-startup214.json')
s=s.replace("BASE/'probes/nes-budget210/check02'", "BASE/'probes/nes-runtime213/check01'")
s=s.replace("BASE/'probes/nes-budget210/check02-review.json'", "BASE/'probes/nes-runtime213/check01-review.json'")
s=once(s,"prep['changed']['src/'+n]", "(prep['copied']|prep['changed']|prep['added'])['src/'+n]")
s=once(s,"cb=review['callbacks'];assert cb.pop('nes_native_video191_plan')==['budget_plan210']", "cb=review['callbacks'];assert cb['nes_resident211_slot']==['resident_plan213']")
for x,y in [('GAME 213','GAME 214'),('game213.nes','game214.nes'),('fpga_n213.bi3','fpga_n214.bi3'),('last-213.txt','last-214.txt'),('nes-progress-213.txt','nes-progress-214.txt'),('nes-budget-213.txt','nes-budget-214.txt'),('NES-GAME213-DEV','NES-GAME214-DEV'),('tools/check_nes_runtime213_arm.py','tools/check_nes_startup214_arm.py')]:s=s.replace(x,y)
ns=dict(prior.__dict__);ns['__file__']=__file__;exec(compile(s,'check214','exec'),ns)
if __name__=='__main__':ns['main']()
