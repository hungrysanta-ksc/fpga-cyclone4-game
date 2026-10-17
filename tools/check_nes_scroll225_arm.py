# SPDX-License-Identifier: MIT
"""Full linked225 RUN/IRQ bound; preserve223 startup, input/audio and wire."""
import check_nes_ingress223_arm as prior
s=prior.s.replace('preparation-ingress223.json','preparation-scroll225.json')
for a,b in [('GAME 223','GAME 225'),('game223.nes','game225.nes'),('fpga_n223.bi3','fpga_n225.bi3'),('last-223.txt','last-225.txt'),('nes-progress-223.txt','nes-progress-225.txt'),('nes-budget-223.txt','nes-budget-225.txt'),('NES-GAME223-DEV','NES-GAME225-DEV'),('tools/check_nes_ingress223_arm.py','tools/check_nes_scroll225_arm.py')]:s=s.replace(a,b)
ns=dict(prior.ns);ns['__file__']=__file__;exec(compile(s,'check225','exec'),ns)
if __name__=='__main__':ns['main']()
