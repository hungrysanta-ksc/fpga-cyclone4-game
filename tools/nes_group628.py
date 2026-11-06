# SPDX-License-Identifier: MIT
"""Extend 624 with checked four-byte patches to the inactive map."""
import argparse
from pathlib import Path
from unittest.mock import patch
import nes_header546
import nes_raw624
from nes_raw506 import once

DECODE = """
 c.label('header628')
 lda(0x1201);c.emit(0x29,255,0,0xc9,2,0);cond(0xd0,'bad_packet')
 lda(0x120a);c.emit(0xc9,0,8);cond(0x90,'bad_packet');c.emit(0x89,63,0);cond(0xd0,'bad_packet')
 lda(0x120c);sta(0x1260)
 lda(0x120e);cond(0xf0,'bad_packet');c.emit(0xc9,193,0);cond(0xb0,'bad_packet')
 c.emit(0x89,63,0);cond(0xd0,'bad_packet');sta(0x120c)
 for _ in range(5):c.emit(0x4a)
 c.emit(0x18,0x69,8,0);sta(0x1262);cmp(0x1260);c.branch(0x90,'size628');cond(0xd0,'bad_packet')
 c.label('size628');lda(0x1034);c.emit(0x0a,0x0a,0xaa)
 c.long(0xaf,0x400010);c.long(0x0f,0x400012);cond(0xf0,'bad_packet')
 for i in (0,2):
  c.long(0xaf,0x400010+i);c.absolute(0xdd,0x14d0+i);cond(0xd0,'bad_packet')
 c.jump('data')
 c.label('decode628');c.store(0x7c,0x7f);c.emit(0xc2,0x20)
 c.absolute(0x9c,0x1266);c.absolute(0x9c,0x1268);c.emit(0xa0,0,0)
 c.label('row628');c.emit(0x98)
 for _ in range(5):c.emit(0x4a)
 c.emit(0xaa);c.long(0xbf,0x400018);sta(0x1264);c.absolute(0xae,0x1262)
 c.label('group628');c.absolute(0x4e,0x1264);c.branch(0x90,'verify628')
 c.emit(0x8a,0x18,0x69,4,0);cmp(0x1260);c.branch(0x90,'copy628');cond(0xd0,'bad_packet')
 c.label('copy628');c.long(0xbf,0x400010);c.emit(0x97,0x7a,0xc8,0xc8)
 c.long(0xbf,0x400012);c.emit(0x97,0x7a,0x88,0x88,0xe8,0xe8,0xe8,0xe8)
 c.label('verify628')
 for _ in (0,1):
  c.emit(0xb7,0x7a,0x18);c.absolute(0x6d,0x1266);sta(0x1266)
  c.emit(0x18);c.absolute(0x6d,0x1268);sta(0x1268);c.emit(0xc8,0xc8)
 c.emit(0x98,0x89,63,0);c.branch(0xd0,'group628');c.absolute(0x8e,0x1262)
 call(c,'service');lda(0x1236);cond(0xd0,'stop_packet')
 c.absolute(0xcc,0x120c);c.branch(0x90,'row628')
 lda(0x1262);cmp(0x1260);cond(0xd0,'bad_packet')
 for i in (0,2):
  c.long(0xaf,0x400014+i);cmp(0x1266+i);cond(0xd0,'bad_packet')
 c.jump('accepted')
"""


def extend(s):
    s=once(s,"0xc9,9,0);c.branch(0x90,'packed_header181')","0xc9,10,0);c.branch(0x90,'packed_header181')")
    s=once(s," c.emit(0xc9,8,0);cond(0xf0,'repeat227')"," c.emit(0xc9,9,0);cond(0xf0,'header628')\n c.emit(0xc9,8,0);cond(0xf0,'repeat227')")
    s=once(s," lda(0x1200);c.emit(0xc9,4);c.branch(0xf0,'repeated1815')"," lda(0x1200);c.emit(0xc9,9);cond(0xf0,'decode628');c.emit(0xc9,4);c.branch(0xf0,'repeated1815')")
    s=once(s," c.label('service');",DECODE+"\n c.label('service');")
    s=once(s,"call(c,'maps181')","call(c,'invalidate628');call(c,'maps181')")
    s=once(s,"c.label('fail');sta(0x122a)","c.label('fail');call(c,'invalidate628');sta(0x122a)")
    s=once(s,'c.store(0x1236,1)','c.store(0x1236,1);c.emit(0xc2,0x20);call(c,\'invalidate628\');c.emit(0xe2,0x20)')
    s=once(s," c.label('bad_header');",""" c.label('invalidate628')
 for i in range(0,8,2):c.absolute(0x9c,0x14d0+i)
 c.emit(0x60)
 c.label('bad_header');""")
    # Only a successful SEAL writes status 1. Publish after the real ACK strobe.
    return once(s,'c.absolute(0xee,0x1220);lda(0x1228)',"""lda(0x1228);c.branch(0xd0,'unpublished628')
 lda(0x1200);c.emit(0x29,255,0,0xc9,3,0);c.branch(0xd0,'unpublished628')
 lda(0x1034);c.emit(0x0a,0x0a,0xaa)
 for i in (0,2):
  lda(0x1222+i);c.absolute(0x9d,0x14d0+i)
 c.label('unpublished628');c.absolute(0xee,0x1220);lda(0x1228)""")


def build(out):
    header=nes_header546.header
    with patch.object(nes_header546,'header',lambda s:extend(header(s))):
        nes_raw624.build(out)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('out',type=Path)
    build(p.parse_args().out)
