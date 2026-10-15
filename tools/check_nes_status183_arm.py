# SPDX-License-Identifier: MIT
"""Full RUN/IRQ bound for next-block metadata reuse; unchanged182 DMA."""
import check_nes_dma182_arm as prior
from nes_clip178 import replace
source=prior.source
for a,b in [('GAME182-DEV','GAME183-DEV'),('GAME 182.nh1','GAME 183.nh1'),('progress-182.txt','progress-183.txt'),('last-182.txt','last-183.txt')]:source=replace(source,a,b)
source=replace(source,"'tools/check_nes_dma182_arm.py','tools/nes_dma182.py','src/nes/firmware/nes_dma182.inc'","'tools/check_nes_status183_arm.py','tools/nes_status183.py','tools/nes_dma182.py','src/nes/firmware/nes_dma182.inc'")
source=replace(source,'result.update(dma_packet_bytes=259,','result.update(status_cache_bytes=9,dma_packet_bytes=259,')
ns=dict(prior.namespace);exec(compile(source,'check_status183','exec'),ns)
if __name__=='__main__':ns['main']()
