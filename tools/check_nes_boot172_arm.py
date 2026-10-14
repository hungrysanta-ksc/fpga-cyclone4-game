# SPDX-License-Identifier: MIT
"""Recompute linked RUN/IRQ bounds including the bounded pre-BEGIN gate."""
import check_nes_prefetch171_arm as prior
source=prior.source
for a,b in [('GAME171-DEV','GAME172-DEV'),('GAME 171.nh1','GAME 172.nh1'),('progress-171.txt','progress-172.txt'),('last-171.txt','last-172.txt')]:
 assert a in source;source=source.replace(a,b)
source=source.replace("'tools/check_nes_prefetch171_arm.py','tools/nes_prefetch171_mcu.py'", "'tools/check_nes_boot172_arm.py','tools/nes_boot172_mcu.py','src/nes/firmware/nes_boot172.inc'")
source=source.replace('171 MCU identity only;170 runtime/transport unchanged. FIFO FPGA assessed separately.','172 readiness gate included in RUN stack;171 FIFO unchanged, ROM-only update assessed separately.')
anchor="if n!='nes_menu_diagnostic.c':assert actual==h,n"
assert anchor in source
source=source.replace(anchor,"""if n=='nes_runtime_board165.inc':
   text=(a.arm/'src'/n).read_text()
   restored=text.replace('#include "nes_boot172.inc"\\n','').replace(' if(!native_boot172(io)){native_io165=NULL;return;}\\n','')
   assert hashlib.sha256(restored.encode()).hexdigest()==h,n
  elif n!='nes_menu_diagnostic.c':assert actual==h,n""")
namespace=dict(prior.namespace);exec(compile(source,'check_boot172','exec'),namespace)
if __name__=='__main__':namespace['main']()
