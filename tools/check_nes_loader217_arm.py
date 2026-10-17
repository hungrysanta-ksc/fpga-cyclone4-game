# SPDX-License-Identifier: MIT
"""Linked217 identity-only ARM, same215 runtime and IRQ reserve."""
import check_nes_plan215_arm as prior
s=prior.s.replace('preparation-plan215.json','preparation-loader217.json')
for x,y in [('GAME 215','GAME 217'),('game215.nes','game217.nes'),('fpga_n215.bi3','fpga_n217.bi3'),('last-215.txt','last-217.txt'),('nes-progress-215.txt','nes-progress-217.txt'),('nes-budget-215.txt','nes-budget-217.txt'),('NES-GAME215-DEV','NES-GAME217-DEV'),('tools/check_nes_plan215_arm.py','tools/check_nes_loader217_arm.py')]:s=s.replace(x,y)
ns=dict(prior.ns);ns['__file__']=__file__;exec(compile(s,'check217','exec'),ns)
if __name__=='__main__':ns['main']()
