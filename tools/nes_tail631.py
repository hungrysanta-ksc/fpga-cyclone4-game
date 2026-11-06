# SPDX-License-Identifier: MIT
"""Checked whole-OAM and scroll-prefix packets for the 624 diagnostic client."""
import argparse
from pathlib import Path
from unittest.mock import patch
import nes_header546
import nes_raw624
from nes_raw506 import once

# Both layouts begin at zero. data still checks identity, sequential coverage
# and the expanded section limit before any write to candidate bank 7F.
DECODER="""
 c.label('header631');checkimm(0x120a,0)
 lda(0x1201);c.emit(0x29,255,0,0xc9,4,0);c.branch(0xd0,'scrollhead631')
 checkimm(0x120c,117);checkimm(0x120e,544);c.jump('span631')
 c.label('scrollhead631');c.emit(0xc9,5,0);cond(0xd0,'bad_packet')
 checkimm(0x120c,22);checkimm(0x120e,1121)
 c.label('span631');lda(0x120e);sta(0x120c);c.jump('data')
 c.label('decode631');c.emit(0xc2,0x20,0xba);c.absolute(0x8e,0x1262)
 imm(0x8000);sta(0x4300);imm(16);sta(0x4302);imm(0x40);sta(0x4304)
 lda(0x1201);c.emit(0x29,255,0,0xc9,4,0);cond(0xf0,'oam631')
 # Write the scroll prefix and fill only up to offset 1121. The raw HDMA
 # receipt starts at 1121; later packets and their receipts are independent.
 imm(21);call(c,'dma631');imm(0x8008);sta(0x4300);imm(37);sta(0x4302)
 c.emit(0xa2,17,0);c.label('scrollchunk631');imm(64);call(c,'dma631')
 c.emit(0xca);c.branch(0xd0,'scrollchunk631');imm(12);call(c,'dma631');c.jump('finish631')
 c.label('oam631');imm(64);call(c,'dma631');imm(48);call(c,'dma631')
 lda(0x7a);c.emit(0x18,0x69,112,0,0xaa);imm(6);sta(0x1260)
 c.label('oamchunk631');call(c,'guard631')
 for start in (0,2):
  c.long(0xaf,0x400080+start)
  for part in range(16):c.long(0x9f,0x7f0000+4*part+start)
 c.emit(0x8a,0x18,0x69,64,0,0xaa);c.absolute(0xce,0x1260);c.branch(0xf0,'oamtail631');c.jump('oamchunk631')
 c.label('oamtail631');call(c,'guard631')
 for start in (0,2):
  c.long(0xaf,0x400080+start)
  for part in range(4):c.long(0x9f,0x7f0000+4*part+start)
 lda(0x7a);c.emit(0x18,0x69,0,2);sta(0x2181)
 imm(0x8008);sta(0x4300);imm(132);sta(0x4302);imm(32);call(c,'dma631')
 c.label('finish631');call(c,'guard631');c.jump('accepted')
 c.label('dma631');sta(0x4305);call(c,'guard631')
 c.emit(0xe2,0x20);c.store(0x420b,1);c.emit(0xc2,0x20,0x60)
 c.label('guard631');call(c,'service');lda(0x1236);c.branch(0xf0,'resume631')
 # Both direct and nested guard calls return to the same packet cancellation.
 c.absolute(0xae,0x1262);c.emit(0x9a);c.jump('stop_packet')
 c.label('resume631');c.emit(0x60)
"""

def extend(src):
    s=once(src,"0xc9,9,0);c.branch(0x90,'packed_header181')","0xc9,10,0);c.branch(0x90,'packed_header181')")
    s=once(s," c.emit(0xc9,8,0);cond(0xf0,'repeat227')"," c.emit(0xc9,9,0);cond(0xf0,'header631')\n c.emit(0xc9,8,0);cond(0xf0,'repeat227')")
    s=once(s," lda(0x1200);c.emit(0xc9,4);c.branch(0xf0,'repeated1815')"," lda(0x1200);c.emit(0xc9,9);cond(0xf0,'decode631');c.emit(0xc9,4);c.branch(0xf0,'repeated1815')")
    return once(s," c.label('service');",DECODER+"\n c.label('service');")

def build(out):
    old=nes_header546.header
    with patch.object(nes_header546,'header',lambda s:extend(old(s))):
        nes_raw624.build(out)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('out',type=Path);build(p.parse_args().out)
