"""Exercise SRAM D0, normal retirement, first-input CRC rejection, STOP and menu gates."""
import argparse
import json
from pathlib import Path

from check_nes_menu533 import check
from check_nes_sram897 import check_game_path
from guard_nes_output852 import run
from nes_raw506 import once, sha
from oam_nes_899 import PROBES, TAG, WORK


def reject_oam(temp):
    trial = temp/f'nes-tile821-early-jointmirror-p1-{TAG}'
    def damage(lua, labels):
        # Same valid op9 shape and OAM contents, wrong last-ACK serial.
        check = ' if pb(0)==7 then tile=tilePayload[index]'
        return once(lua,check," if pw(8)==910 and pb(0)==9 and pb(1)==4 then "
                    "packet=packet:sub(1,-2)..string.char(packet:byte(-1)~1) end\n"+check)
    return run(temp,trial,'oam-serial',column_client=PROBES/'nes-trial890/client02',
               select_packet=lambda b,g:g==910 and b[:2]==bytes((9,4)),adapt_lua=damage)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('arm','oam'))
    p.add_argument('temp',type=Path)
    a=p.parse_args()
    src=WORK/'link-g/src'
    if a.action=='arm':
        cases,ram,entry=check_game_path(src)
        result=dict(SRAM=hex(ram),entry=hex(entry),cases=cases,menu=check(src,'897'),
                    firmware=sha(src/'obj-nes-100/firmware.stm'))
    else:
        result=reject_oam(a.temp)
    (WORK/f'check-{a.action}.json').write_text(json.dumps(result,indent=2)+'\n')
