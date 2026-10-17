# SPDX-License-Identifier: MIT
"""Linked216 identity-only ARM, same215 runtime and IRQ reserve."""
import check_nes_plan215_arm as prior
s=prior.s.replace('preparation-plan215.json','preparation-wait216.json')
for x,y in [('GAME 215','GAME 216'),('game215.nes','game216.nes'),('fpga_n215.bi3','fpga_n216.bi3'),('last-215.txt','last-216.txt'),('nes-progress-215.txt','nes-progress-216.txt'),('nes-budget-215.txt','nes-budget-216.txt'),('NES-GAME215-DEV','NES-GAME216-DEV'),('tools/check_nes_plan215_arm.py','tools/check_nes_wait216_arm.py')]:s=s.replace(x,y)
ns=dict(prior.ns);ns['__file__']=__file__;exec(compile(s,'check216','exec'),ns)
if __name__=='__main__':ns['main']()
