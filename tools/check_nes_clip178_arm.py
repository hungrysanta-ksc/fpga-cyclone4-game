# SPDX-License-Identifier: MIT
"""Recompute full linked RUN/IRQ with the paired178 converter and sink."""
import check_nes_boundary177_arm as prior
source=prior.source
for a,b in [('GAME177-DEV','GAME178-DEV'),('GAME 177.nh1','GAME 178.nh1'),('progress-177.txt','progress-178.txt'),('last-177.txt','last-178.txt')]:
    assert a in source;source=source.replace(a,b)
source=source.replace("'tools/check_nes_boundary177_arm.py','tools/nes_boundary177_mcu.py','tools/nes_snapshot175_mcu.py','tools/nes_lifecycle175_mcu.py'", "'tools/check_nes_clip178_arm.py','tools/nes_clip178_mcu.py','tools/nes_clip178.py'")
source=source.replace('174 cross-tile converter and receiver included in linked RUN stack;173 timing counters and172 boot gate preserved. FPGA timing and pixel equivalence assessed separately.', '178 paired mask converter/header/20-byte sink included in linked RUN stack;177 runtime and platform retained. No FPGA fit or hardware approval.')
namespace=dict(prior.namespace)
exec(compile(source,'check_clip178','exec'),namespace)
if __name__=='__main__':namespace['main']()
