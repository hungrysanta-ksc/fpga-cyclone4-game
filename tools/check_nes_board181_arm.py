# SPDX-License-Identifier: MIT
"""Recompute the paired181 full linked RUN/IRQ bound; preserve platform review."""
import check_nes_minreject180_arm as prior
from nes_reject180 import replace
source=prior.source
for a,b in [('GAME180-DEV','GAME181-DEV'),('GAME 180.nh1','GAME 181.nh1'),
            ('progress-180.txt','progress-181.txt'),('last-180.txt','last-181.txt')]:
    source=replace(source,a,b)
source=replace(source,
    "'tools/check_nes_minreject180_arm.py','tools/nes_minreject180_mcu.py','tools/nes_reject180.py'",
    "'tools/check_nes_board181_arm.py','tools/nes_board181.py','tools/nes_reject180.py'")
source=replace(source,
    '180 names/history version3 only; unchanged178 RUN/converter/sink. Optional history is read after STOP. No FPGA or physical approval.',
    '181 paired receiver/raw converter/24-byte sink included in the recomputed linked RUN graph. Runtime/platform and optional post-STOP history retained. No FPGA or physical approval.')
namespace=dict(prior.namespace)
exec(compile(source,'check_board181','exec'),namespace)
if __name__=='__main__':namespace['main']()
