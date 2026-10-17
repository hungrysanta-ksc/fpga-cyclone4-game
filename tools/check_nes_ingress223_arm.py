# SPDX-License-Identifier: MIT
"""Recompute linked223 receiver/RUN/IRQ bound, preserving222 startup checks."""
import check_nes_startup222_arm as prior
s=prior.s.replace('preparation-startup222.json','preparation-ingress223.json')
for x,y in [('GAME 222','GAME 223'),('game222.nes','game223.nes'),('fpga_n222.bi3','fpga_n223.bi3'),
            ('last-222.txt','last-223.txt'),('nes-progress-222.txt','nes-progress-223.txt'),
            ('nes-budget-222.txt','nes-budget-223.txt'),('NES-GAME222-DEV','NES-GAME223-DEV'),
            ('tools/check_nes_startup222_arm.py','tools/check_nes_ingress223_arm.py')]:s=s.replace(x,y)
ns=dict(prior.ns);ns['__file__']=__file__;exec(compile(s,'check223','exec'),ns)
if __name__=='__main__':ns['main']()
