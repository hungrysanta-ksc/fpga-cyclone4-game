# SPDX-License-Identifier: MIT
"""Exercise the linked map gates and reuse the original first/END guards on each ELF."""
import argparse
import json
from pathlib import Path
from check_nes_frontier536 import offer,exercise,end_guard,sha

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True)
    p.add_argument('--policy',choices=('add','both','only'),required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    first=[exercise(a.arm,k) for k in ('DATA','RLE','empty','last_row','three_credits','bulk','STOP','bad_E8_CRC','ambiguous_E1')]
    end=[end_guard(a.arm,k) for k in ('normal','busy','bad_crc','bad_identity','STOP_after_refresh','ambiguous_E1')]
    gated=[]
    if a.policy!='only':
        for k in ('normal','refreshed','full','bad_identity','sentinel','end','old_bulk','bulk','STOP','bad_E8_CRC','ambiguous_E1'):
            gated.append(offer(a.arm,k,early=True))
        for early,count in ((False,0),(True,1)):
            for first_offer in (False,True):
                gated.append(offer(a.arm,'normal',early=early,count=count,first=first_offer,
                                   expect_deferred=not first_offer or a.policy=='both'))
        gated.append(offer(a.arm,'normal',early=True,first=True))
    a.out.write_text(json.dumps(dict(elf_firmware=sha(a.arm/'obj-nes-100/firmware.stm'),first=first,end=end,gated=gated),indent=2)+'\n')
