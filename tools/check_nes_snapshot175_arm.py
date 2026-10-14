# SPDX-License-Identifier: MIT
"""A5 names/label only MCU; full linked RUN/IRQ bounds recomputed."""
import check_nes_cross174_arm as prior
source=prior.source
for a,b in [('GAME174-DEV','GAME175-DEV'),('GAME 174.nh1','GAME 175.nh1'),('progress-174.txt','progress-175.txt'),('last-174.txt','last-175.txt')]:
    assert a in source;source=source.replace(a,b)
source=source.replace("'tools/check_nes_cross174_arm.py','tools/nes_cross174.py'", "'tools/check_nes_snapshot175_arm.py','tools/nes_snapshot175_mcu.py','tools/nes_lifecycle175_mcu.py'")
namespace=dict(prior.namespace)
exec(compile(source,'check_snapshot175','exec'),namespace)
if __name__=='__main__':namespace['main']()
