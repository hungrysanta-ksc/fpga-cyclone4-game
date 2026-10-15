# SPDX-License-Identifier: MIT
"""Retain181 platform/library review, recompute linked DMA RUN and IRQ stack."""
import check_nes_paired181_arm as prior
from nes_clip178 import replace

source=prior.source
for a,b in [('GAME181-DEV','GAME182-DEV'),('GAME 181.nh1','GAME 182.nh1'),
            ('progress-181.txt','progress-182.txt'),('last-181.txt','last-182.txt')]:
    source=replace(source,a,b)
source=replace(source,"  elif n!='nes_menu_diagnostic.c':assert actual==h,n", """  elif n=='nes_native165_bulk.inc':
   baseline=ROOT.parent/'probes/nes-paired181/evidence/arm02/src'/n
   assert sha(baseline)==h
   assert (a.arm/'src'/n).read_text()==bulk(baseline.read_text())
  elif n!='nes_menu_diagnostic.c':assert actual==h,n""")
source=replace(source," result.update(profile_trace_bytes=40", """ assert 'nes182_stuck' in new
 assert 'cpsid' in new['nes182_stuck'] and '<nes_cf86_fail094>' in new['nes182_stuck']
 assert 'bx\\tlr' not in new['nes182_stuck']
 assert (a.arm/'src/nes_dma182.inc').read_bytes()==(ROOT/'src/nes/firmware/nes_dma182.inc').read_bytes()
 result.update(dma_packet_bytes=259,spi_hz=2625000,profile_trace_bytes=40""")
source=replace(source,"'tools/check_nes_paired181_arm.py','tools/nes_paired181.py'",
               "'tools/check_nes_dma182_arm.py','tools/nes_dma182.py','src/nes/firmware/nes_dma182.inc'")
namespace=dict(prior.namespace)
from nes_dma182 import bulk
namespace['bulk']=bulk
exec(compile(source,'check_dma182','exec'),namespace)
if __name__=='__main__':namespace['main']()
