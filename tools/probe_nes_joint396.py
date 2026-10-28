# SPDX-License-Identifier: MIT
"""Actual396 ARM/frontier/sharedSPI/IRQ/ROM with3584/512 prestaging.
Native65816 service is retained394;fullCPU/WCET remains outside this model."""
import probe_nes_jobs394_joint as old
from nes_joint396 import arm,rtl
from nes_control396 import bench
old.apply_arm=lambda d,cold_quantum=0:arm(d)
old.apply_rtl=rtl
prepare=old.prepare
adapt=old.adapt_tb
old.adapt_tb=lambda s:bench(adapt(s))
def fresh(d,last,cold_quantum=0):
 src=prepare(d,last,cold_quantum)+['nes_stage396.sv','nes_check396.sv','nes_walk396.sv']
 import json
 from nes_delta231 import sha
 (d/'manifest396.json').write_text(json.dumps(dict(RTL={n:sha(d/n)for n in src},ELF=sha(d/'output.elf'),test=sha(d/'joint266_tb.sv')),indent=2)+'\n')
 return src
old.prepare=fresh;old.__file__=__file__
if __name__=='__main__':old.main()
