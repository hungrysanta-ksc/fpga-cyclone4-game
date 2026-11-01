# SPDX-License-Identifier: MIT
"""Issue one accepted 64-byte map row or one closed tile command while idle."""
import argparse
import json
from pathlib import Path

import nes_prefix523 as prefix
from nes_idle524 import arbitrate, packet


class MapRows:
    late_beam = None

    @staticmethod
    def select(c):
        # Prefer the newest map range even when older tiles are outstanding.
        # mark212 checks alignment, bounds and duplicate rows. At an idle poll
        # the packet ACK follows the completed copy into the inactive WRAM bank.
        c.absolute(0xad,0x1250);c.absolute(0xcd,0x1252);c.branch(0xf0,'empty526')
        c.emit(0x38,0xe9,8,0,0xaa)
        c.long(0xbf,0x7e4000);c.emit(0x29,0,0x70,0xc9,0,0x50);c.branch(0xf0,'row526')
        c.absolute(0xec,0x1252);c.branch(0xf0,'empty526')  # open non-map tail
        c.absolute(0xae,0x1252)
        c.long(0xbf,0x7e4000);c.emit(0x29,0,0x70,0xc9,0,0x50);c.branch(0xf0,'row526')
        c.long(0xbf,0x7e4004);c.emit(0xc9,1,8);c.branch(0xb0,'empty526')
        c.emit(0xa8);c.branch(0x80,'selected526')
        c.label('empty526');c.jump('skip523')
        c.label('row526');c.emit(0xa0,64,0)
        c.label('selected526')

    @staticmethod
    def retire(c):
        # X and Y survive service and arbitration. Only mutate the selected
        # range after synchronous MDMAEN returns. Coverage lives separately.
        c.emit(0x98);c.long(0xdf,0x7e4004);c.branch(0xf0,'whole526')
        for address in (0x7e4000,0x7e4002):
            c.long(0xbf,address);c.emit(0x18,0x69,64,0);c.long(0x9f,address)
        c.long(0xbf,0x7e4004);c.emit(0x38,0xe9,64,0);c.long(0x9f,0x7e4004)
        c.branch(0x80,'retired526')
        c.label('whole526');c.emit(0x8a,0x18,0x69,8,0);c.absolute(0xcd,0x1250)
        c.branch(0xf0,'pop526');c.absolute(0x8d,0x1252);c.branch(0x80,'retired526')
        c.label('pop526');c.absolute(0x8e,0x1250);c.absolute(0xec,0x1252)
        c.branch(0xd0,'retired526')
        # With no live entries append212 must never extend a retired tile.
        c.absolute(0x9c,0x1250);c.absolute(0x9c,0x1252)
        c.label('retired526')


class LateMapRows(MapRows):
    @staticmethod
    def late_beam(c,defer):
        # 64-byte map only. The 16-bit beam latch already rejected line 256+.
        c.emit(0xc9,233);c.branch(0x90,'map_beam_ok526')
        c.emit(0xc9,255);c.branch(0xb0,defer)
        c.long(0xbf,0x7e4001);c.emit(0x29,0x70,0xc9,0x50);c.branch(0xd0,defer)
        c.label('map_beam_ok526')


def build(out,before_beam=None,late=False):
    policy=LateMapRows if late else MapRows
    r=prefix.build(out,emitter=lambda c:prefix.emit(c,before_beam,arbitrate,policy),
                   fill=True,packet_edit=packet,upload_edit=prefix.upload)
    r.update(candidate='map526',map_chunk_B=64,prefix_last_line=232,map_last_line=254 if late else 232,new_WRAM_B=0)
    (out/'build.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n')
    return r


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--late-map',action='store_true')
    a=p.parse_args();print(build(a.out,late=a.late_map)['body_bytes'])
