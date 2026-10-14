# SPDX-License-Identifier: MIT
"""Names/label only177; recompute full-link RUN/IRQ bounds using174 review."""
import check_nes_cross174_arm as prior
source=prior.source
for a,b in [('GAME174-DEV','GAME177-DEV'),('GAME 174.nh1','GAME 177.nh1'),('progress-174.txt','progress-177.txt'),('last-174.txt','last-177.txt')]:
 assert a in source;source=source.replace(a,b)
source=source.replace("'tools/check_nes_cross174_arm.py','tools/nes_cross174.py'", "'tools/check_nes_boundary177_arm.py','tools/nes_boundary177_mcu.py','tools/nes_snapshot175_mcu.py','tools/nes_lifecycle175_mcu.py'")
namespace=dict(prior.namespace)
exec(compile(source,'check_boundary177','exec'),namespace)
if __name__=='__main__':namespace['main']()
