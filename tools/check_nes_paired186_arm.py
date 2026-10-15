# SPDX-License-Identifier: MIT
"""Recompute full linked186 RUN/IRQ; only sink group planning changes."""
import check_nes_paired185_arm as prior
from nes_clip178 import replace
source=prior.source
for a,b in [('GAME185-DEV','GAME186-DEV'),('GAME 185.nh1','GAME 186.nh1'),('progress-185.txt','progress-186.txt'),('last-185.txt','last-186.txt')]:source=replace(source,a,b)
source=replace(source,"'tools/check_nes_paired185_arm.py','tools/nes_paired185.py'","'tools/check_nes_paired186_arm.py','tools/nes_paired186.py','tools/nes_copy186.py','tools/check_nes_paired185_arm.py','tools/nes_paired185.py'")
source=replace(source,'1851 map inheritance sink','1861 grouped map inheritance sink')
ns=dict(prior.ns);exec(compile(source,'check_paired186','exec'),ns)
if __name__=='__main__':ns['main']()
