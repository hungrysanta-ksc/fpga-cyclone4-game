# SPDX-License-Identifier: MIT
"""Diagnostic op9: fully specify three right-page rows, each literal34 + zero30."""
import argparse
from pathlib import Path
from unittest.mock import patch
import nes_header546
import nes_raw624
from nes_raw506 import once

# The generic data path checks the expanded end and coverage before decode.
# Packet offset 17 is the validated zero in the first row descriptor.
DECODER="""
 c.label('header630');lda(0x1201);c.emit(0x29,255,0,0xc9,2,0);cond(0xd0,'bad_packet')
 lda(0x120a);c.emit(0xc9,0,8);cond(0x90,'bad_packet');c.emit(0x89,63,0);cond(0xd0,'bad_packet')
 lda(0x120c);c.emit(0xc9,108,0);cond(0xd0,'bad_packet')
 lda(0x120e);c.emit(0xc9,192,0);cond(0xd0,'bad_packet');sta(0x120c)
 for row in range(3):
  c.long(0xaf,0x400010+row*36);c.emit(0xc9,34,0);cond(0xd0,'bad_packet')
 c.jump('data')
 c.label('decode630');c.emit(0xc2,0x20)
 lda(0x7a);sta(0x2181);c.emit(0xe2,0x20);c.store(0x2183,1);c.emit(0xc2,0x20)
 imm(18);sta(0x1262)
 c.label('row630');call(c,'service');lda(0x1236);cond(0xd0,'stop_packet')
 imm(0x8000);sta(0x4300);lda(0x1262);sta(0x4302);imm(0x40);sta(0x4304)
 imm(34);sta(0x4305);c.emit(0xe2,0x20);c.store(0x420b,1);c.emit(0xc2,0x20)
 imm(0x8008);sta(0x4300);imm(17);sta(0x4302)
 imm(30);sta(0x4305);c.emit(0xe2,0x20);c.store(0x420b,1);c.emit(0xc2,0x20)
 lda(0x1262);c.emit(0x18,0x69,36,0);sta(0x1262);c.emit(0xc9,126,0);c.branch(0xd0,'row630')
 c.jump('accepted')
"""

def extend(s):
    s=once(s,"0xc9,9,0);c.branch(0x90,'packed_header181')","0xc9,10,0);c.branch(0x90,'packed_header181')")
    s=once(s," c.emit(0xc9,8,0);cond(0xf0,'repeat227')"," c.emit(0xc9,9,0);cond(0xf0,'header630')\n c.emit(0xc9,8,0);cond(0xf0,'repeat227')")
    s=once(s," lda(0x1200);c.emit(0xc9,4);c.branch(0xf0,'repeated1815')"," lda(0x1200);c.emit(0xc9,9);cond(0xf0,'decode630');c.emit(0xc9,4);c.branch(0xf0,'repeated1815')")
    return once(s," c.label('service');",DECODER+"\n c.label('service');")

def build(out):
    old=nes_header546.header
    with patch.object(nes_header546,'header',lambda s:extend(old(s))):
        nes_raw624.build(out)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('out',type=Path)
    build(p.parse_args().out)
