# SPDX-License-Identifier: MIT
"""Recompute full227 linked RUN/IRQ budget without changing the1024B gate."""
import check_nes_fast226_arm as prior
from nes_fast226 import once
s=prior.s.replace('preparation-fast226.json','preparation-repeat227.json')
s=once(s,"assert sha(ROOT/'tools/nes_fast226.py')==prep['source_sha256']",
       "for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n")
s=once(s,"public_sources={'tools/nes_fast226.py':prep['source_sha256']}|",
       "public_sources=prep['public_sources']|")
for x,y in [('GAME 226','GAME 227'),('game226.nes','game227.nes'),('fpga_n226.bi3','fpga_n227.bi3'),
 ('last-226.txt','last-227.txt'),('nes-progress-226.txt','nes-progress-227.txt'),('nes-budget-226.txt','nes-budget-227.txt'),
 ('NES-GAME226-DEV','NES-GAME227-DEV'),('tools/check_nes_fast226_arm.py','tools/check_nes_repeat227_arm.py')]:
 s=s.replace(x,y)
ns=dict(prior.ns);ns['__file__']=__file__;exec(compile(s,'check227','exec'),ns)
if __name__=='__main__':ns['main']()
