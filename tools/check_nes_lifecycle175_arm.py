# SPDX-License-Identifier: MIT
"""Recompute the linked175 RUN/IRQ bounds; runtime is unchanged174."""
import check_nes_cross174_arm as prior
source=prior.source
for a,b in [('GAME174-DEV','GAME175-DEV'),('GAME 174.nh1','GAME 175.nh1'),('progress-174.txt','progress-175.txt'),('last-174.txt','last-175.txt')]:
    assert a in source;source=source.replace(a,b)
source=source.replace("'tools/check_nes_cross174_arm.py','tools/nes_cross174.py'", "'tools/check_nes_lifecycle175_arm.py','tools/nes_lifecycle175_mcu.py'")
anchor="elif n!='nes_menu_diagnostic.c':assert actual==h,n"
assert source.count(anchor)==1
source=source.replace(anchor,"""elif n=='nes_run136.inc':
   text=(a.arm/'src'/n).read_text()
   assert text.count('rx[5]!=2||rx[6]!=96||rx[7]!=1')==1
   restored=text.replace('rx[5]!=2||rx[6]!=96||rx[7]!=1','rx[5]!=1||rx[6]!=96||rx[7]!=1')
   assert hashlib.sha256(restored.encode()).hexdigest()==h,n
  elif n!='nes_menu_diagnostic.c':assert actual==h,n""")
namespace=dict(prior.namespace)
exec(compile(source,'check_lifecycle175','exec'),namespace)
if __name__=='__main__':namespace['main']()
