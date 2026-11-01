# SPDX-License-Identifier: MIT
"""Execute a closed command only while the receiver has no packet to consume."""
import argparse
import json
from pathlib import Path

import nes_prefix523 as prefix
from nes_raw506 import once


def arbitrate(c):
    # M=8. A newly ready head is held until ACK. Leave the cursor untouched
    # on both deferrals. A STOP without a packet has no identity to acknowledge.
    c.label('priority524')
    c.absolute(0xad,0x6001);c.branch(0x10,'ready524')
    c.store(0x1236,1)
    c.branch(0x80,'skip8_523')
    c.label('ready524');c.absolute(0xad,0x6000);c.emit(0x29,1)
    c.branch(0xd0,'skip8_523')
    c.label('grant524')


def packet(source):
    source=once(source,"c.absolute(0x9c,0x1250)","c.absolute(0x9c,0x1250);c.absolute(0x9c,0x1252)")
    return once(source,"cond(0xf0,'poll')","""cond(0xd0,'head524')
 # Open transaction only. Poll STOP first on every pass, and recheck
 # STOP and head immediately before the nonpreemptible MDMAEN write.
 lda(0x1228);c.emit(0xc9,1,0);cond(0xd0,'poll')
 call(c,'prefix523');c.jump('poll');c.label('head524')""")


def build(out):
    r=prefix.build(out,emitter=lambda c:prefix.emit(c,before_start=arbitrate),
                   fill=True,packet_edit=packet,upload_edit=prefix.upload)
    r.update(candidate='idle524',prefix_last_line=232,prefix_max_bytes=2048,new_WRAM_B=0)
    (out/'build.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n')
    return r


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    print(build(p.parse_args().out)['body_bytes'])
