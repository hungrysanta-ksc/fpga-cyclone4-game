# SPDX-License-Identifier: MIT
"""Charge the real reuse head and verify the consumer's live WRAM after its ACK."""
import argparse
import math
from pathlib import Path
from analyze_nes_map628 import packets,read
from replay_nes_bank633 import target
from replay_nes_overlap634 import run as overlap
from nes_raw506 import once


def run(a):
    a.feedback=True;a.policy='restore'
    source=packets(a.trace)
    probe=read(a.arm_result)
    head=bytes.fromhex(probe['head'])
    # Charge the whole linked compare and serialization even though the original
    # slot already had a literal OAM head. Four extra SPI bytes, same transfer.
    cost=math.ceil(21477272*(2*(probe['instructions']['compare951']+probe['instructions']['serialize951'])/84000000+4*8/2625000))
    def change(kept,commands):
        return [(t+(cost if i>=13 else 0),head if i==13 else h,b) for i,(t,h,b) in enumerate(kept)]
    def observe(s,labels):
        for gen in range(905,952):
            (a.out/f'expected635-{gen}.bin').write_bytes(target(source[gen],3)+target(source[gen],4))
        s=once(s,'  lastStatus=ack[1];',"""  if pb(0)==9 then
   assert(pw(8)==951 and ack[1]==0 and word(0x1086)==512 and word(0x1088)==544)
   local data=file('expected635-'..pw(8)..'.bin');local base=0x16000+word(0x1020)
   for j=0,1055 do assert(rd(base+j)==data:byte(j+1),'palette/OAM byte '..j) end
  end
  if pb(0)==3 and ack[1]==1 then
   local data=file('expected635-'..pw(8)..'.bin')
   for j=0,511 do assert(emu.read(j,emu.memType.snesCgRam)==(data:byte(j+1)&(j%2==1 and 127 or 255)),'CGRAM '..j) end
   for j=0,543 do assert(emu.read(j,emu.memType.snesSpriteRam)==data:byte(513+j),'OAM '..j) end
  end
  lastStatus=ack[1];""")
        if 'compare635' in labels:
            s=once(s,"if event~='idle524' and event~='ppu_dma'","if event~='proof635' and event~='idle524' and event~='ppu_dma'")
            s+=f"\nemu.addMemoryCallback(function()sample516('proof635',word(0x14da))end,emu.callbackType.exec,{labels['compare635']})\n"
        return s
    active=a.mode=='collapse'
    overlap(a,change_offers=change if active else None,extra_after={17:cost} if active else None,
            source_client=a.reference,real_observer=observe)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('trace','client','out','mesen','reference','arm-result'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--mode',choices=('control','collapse'),required=True)
    run(p.parse_args())
