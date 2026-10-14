# SPDX-License-Identifier: MIT
"""Full linked stack review; one strict optional-history version byte changed."""
import check_nes_clip178_arm as prior
from nes_reject180 import replace
source=prior.source
for a,b in [('GAME178-DEV','GAME180-DEV'),('GAME 178.nh1','GAME 180.nh1'),('progress-178.txt','progress-180.txt'),('last-178.txt','last-180.txt')]:
    source=replace(source,a,b)
source=replace(source,"elif n!='nes_menu_diagnostic.c':assert actual==h,n", """elif n=='nes_run136.inc':
   text=(a.arm/'src'/n).read_text()
   assert text.count('rx[6]!=96||rx[7]!=2||')==1
   restored=text.replace('rx[6]!=96||rx[7]!=2||','rx[6]!=96||rx[7]!=1||')
   assert hashlib.sha256(restored.encode()).hexdigest()==h,n
  elif n!='nes_menu_diagnostic.c':assert actual==h,n""")
source=source.replace("'tools/check_nes_clip178_arm.py','tools/nes_clip178_mcu.py','tools/nes_clip178.py'", "'tools/check_nes_reject180_arm.py','tools/nes_reject180_mcu.py','tools/nes_reject180.py'")
source=source.replace('178 paired mask converter/header/20-byte sink included in linked RUN stack;177 runtime and platform retained. No FPGA fit or hardware approval.', '180 names/history version2 only; unchanged178 RUN/converter/sink. Optional history is read after STOP. No FPGA or physical approval.')
namespace=dict(prior.namespace)
exec(compile(source,'check_reject180','exec'),namespace)
if __name__=='__main__':namespace['main']()
