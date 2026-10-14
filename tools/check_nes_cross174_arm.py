# SPDX-License-Identifier: MIT
"""174: full linked stack/IRQ analysis; unchanged platform-body review from173."""
import check_nes_profile173_arm as prior
source=prior.source
for a,b in [('GAME173-DEV','GAME174-DEV'),('GAME 173.nh1','GAME 174.nh1'),('progress-173.txt','progress-174.txt'),('last-173.txt','last-174.txt')]:
 assert a in source;source=source.replace(a,b)
source=source.replace("'tools/check_nes_profile173_arm.py','tools/nes_profile173.py'", "'tools/check_nes_cross174_arm.py','tools/nes_cross174.py'")
source=source.replace('172 readiness gate included in RUN stack;171 FIFO unchanged, ROM-only update assessed separately.', '174 cross-tile converter and receiver included in linked RUN stack;173 timing counters and172 boot gate preserved. FPGA timing and pixel equivalence assessed separately.')
namespace=dict(prior.namespace)
exec(compile(source,'check_cross174','exec'),namespace)
if __name__=='__main__':namespace['main']()
