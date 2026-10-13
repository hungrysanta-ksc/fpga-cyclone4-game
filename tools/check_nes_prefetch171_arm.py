# SPDX-License-Identifier: MIT
"""Recompute linked RUN/IRQ bounds for171 naming-only MCU using170 checker."""
import check_nes_startup170_arm as prior
source=prior.source
for a,b in [('GAME170-DEV','GAME171-DEV'),('GAME 170.nh1','GAME 171.nh1'),('progress-170.txt','progress-171.txt'),('last-170.txt','last-171.txt')]:
 assert a in source;source=source.replace(a,b)
source=source.replace("'tools/check_nes_startup170_arm.py','tools/nes_startup170.py'", "'tools/check_nes_prefetch171_arm.py','tools/nes_prefetch171_mcu.py','tools/check_nes_startup170_arm.py'")
source=source.replace('170 adds20B first exchange failure trace; full RUN/IRQ graph recomputed. FPGA/SNES169 unchanged.','171 MCU identity only;170 runtime/transport unchanged. FIFO FPGA assessed separately.')
namespace=dict(prior.namespace);exec(compile(source,'check_prefetch171','exec'),namespace)
if __name__=='__main__':namespace['main']()
