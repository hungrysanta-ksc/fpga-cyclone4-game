# SPDX-License-Identifier: MIT
"""Linked220 identity-only ARM, same215 runtime and IRQ reserve."""
import check_nes_plan215_arm as prior
s=prior.s.replace('preparation-plan215.json','preparation-status220.json')
for x,y in [('GAME 215','GAME 220'),('game215.nes','game220.nes'),('fpga_n215.bi3','fpga_n220.bi3'),('last-215.txt','last-220.txt'),('nes-progress-215.txt','nes-progress-220.txt'),('nes-budget-215.txt','nes-budget-220.txt'),('NES-GAME215-DEV','NES-GAME220-DEV'),('tools/check_nes_plan215_arm.py','tools/check_nes_status220_arm.py')]:s=s.replace(x,y)
ns=dict(prior.ns);ns['__file__']=__file__;exec(compile(s,'check220','exec'),ns)
if __name__=='__main__':ns['main']()
