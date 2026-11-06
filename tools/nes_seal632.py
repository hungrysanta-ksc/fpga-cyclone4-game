# SPDX-License-Identifier: MIT
"""Move independent tile and HDMA checks to immutable inputs; retain final map/length checks."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
import nes_header546
import nes_tile619
import nes_raw624
from nes_raw506 import once

# Diagnostic palette packet: 32 literal bytes followed by the selected proofs.
# Bit 0 moves the authoritative 144-byte requirements, bit 1 declares the
# section-5 length, display mask and patch count, bit 2 marks checked HDMA.
EXTRA="""
 c.label('palette632');checkimm(0x14d0,0);checkimm(0x120a,0)
 lda(0x1201);c.emit(0x29,255,0,0xc9,3,0);cond(0xd0,'bad_packet')
 lda(0x120e);cond(0xf0,'bad_packet');c.emit(0xc9,4,0);cond(0xb0,'bad_packet');sta(0x14d0)
 imm(32);sta(0x1260);lda(0x14d0);c.emit(0x89,1,0);c.branch(0xf0,'hdmasize632')
 imm(176);sta(0x1260)
 c.label('hdmasize632');lda(0x14d0);c.emit(0x89,2,0);c.branch(0xf0,'length632')
 lda(0x1260);c.emit(0xaa,0x18,0x69,6,0);sta(0x1260)
 c.label('length632');lda(0x1260);cmp(0x120c);cond(0xd0,'bad_packet')
 lda(0x14d0);c.emit(0x89,2,0);c.branch(0xf0,'tiles632')
 c.long(0xbf,0x400010);cond(0xf0,'bad_packet');c.emit(0xc9,0x5b,0x0d);cond(0xb0,'bad_packet');sta(0x14d2)
 c.long(0xbf,0x400012);c.emit(0xc9,0x18,0);c.branch(0xf0,'mask632');c.emit(0xc9,0x1e,0);cond(0xd0,'bad_packet')
 c.label('mask632');sta(0x14d4);c.long(0xbf,0x400014);c.emit(0xc9,8,0);cond(0xb0,'bad_packet');sta(0x14d6)
 c.label('tiles632');lda(0x14d0);c.emit(0x89,1,0);cond(0xf0,'literal632')
 c.absolute(0xac,0x1254);c.emit(0xa2,0,0)
 c.label('walk632')
 for off in range(0,16,2):
  c.absolute(0xb9,0x1320+off);c.emit(0x49,255,255);c.long(0x3f,0x400030+off);cond(0xd0,'bad_packet')
 c.emit(0x98,0x18,0x69,16,0,0xa8,0x8a,0x18,0x69,16,0,0xaa,0xe0,144,0);cond(0xd0,'walk632')
 call(c,'service');lda(0x1236);cond(0xd0,'stop_packet')
 c.label('literal632');imm(32);sta(0x120c);c.jump('data')
 c.label('earlyhdma632');lda(0x108a);cmp(0x14d2);c.branch(0x90,'return632');cond(0xd0,'bad_packet')
 lda(0x14d2);sta(0x100a);lda(0x14d4);sta(0x123a);lda(0x14d6);sta(0x1240)
 call(c,'compact489');lda(0x1236);cond(0xd0,'stop_packet');cond(0x90,'bad_packet')
 call(c,'validate181');cond(0x90,'bad_packet');lda(0x100a);sta(0x14d8)
 call(c,'service');lda(0x1236);cond(0xd0,'stop_packet')
 imm(4);c.absolute(0x0c,0x14d0)
 c.label('return632');c.jump('accepted194')
"""

def extend(s):
    s=once(s,"0xc9,9,0);c.branch(0x90,'packed_header181')","0xc9,10,0);c.branch(0x90,'packed_header181')")
    s=once(s," c.emit(0xc9,8,0);cond(0xf0,'repeat227')",
           " c.emit(0xc9,9,0);cond(0xf0,'palette632')\n c.emit(0xc9,8,0);cond(0xf0,'repeat227')")
    s=once(s,"c.label('begin');","c.label('begin');c.absolute(0x9c,0x14d0);")
    s=once(s,"c.label('fail');sta(0x122a)","c.label('fail');c.absolute(0x9c,0x14d0);sta(0x122a)")
    s=once(s,"c.store(0x1236,1)","c.store(0x1236,1);c.store(0x14d0,0)")
    s=once(s,"c.absolute(0x9c,0x1228);imm(1);c.jump('reply')","c.absolute(0x9c,0x1228);c.absolute(0x9c,0x14d0);imm(1);c.jump('reply')")
    s=once(s,"c.label('bulk194');","c.label('bulk194');lda(0x14d0);c.emit(0x89,1,0);cond(0xd0,'bad_packet');")
    s=once(s,"c.label('data');","""c.label('data');lda(0x14d0);c.emit(0x89,4,0);c.branch(0xf0,'writable632')
 lda(0x1201);c.emit(0x29,255,0,0xc9,5,0);cond(0xf0,'bad_packet')
 c.label('writable632');""")
    s=once(s,"c.label('accepted');","""c.label('accepted');lda(0x14d0);c.emit(0x89,2,0);c.branch(0xf0,'ordinary632')
 lda(0x1201);c.emit(0x29,255,0,0xc9,5,0);cond(0xf0,'earlyhdma632')
 c.label('ordinary632');""")
    s=once(s,"checkimm(0x120c,168)","""lda(0x14d0);c.emit(0x89,1,0);c.branch(0xf0,'long632')
 checkimm(0x120c,24);c.jump('sizes632')
 c.label('long632');checkimm(0x120c,168);c.label('sizes632')""")
    s=once(s," call(c,'compact489');",""" lda(0x14d0);c.emit(0x89,2,0);c.branch(0xf0,'normal632')
 c.emit(0x89,4,0);cond(0xf0,'bad_packet')
 for a,b in ((0x100a,0x14d2),(0x123a,0x14d4),(0x1240,0x14d6)):
  lda(a);cmp(b);cond(0xd0,'bad_packet')
 lda(0x14d8);sta(0x100a);c.jump('validated632')
 c.label('normal632');call(c,'compact489');""")
    s=once(s,"call(c,'coverage212');","c.label('validated632');call(c,'coverage212');")
    return once(s," c.label('service');",EXTRA+"\n c.label('service');")

def build(out):
    old_header=nes_header546.header
    old_coverage=nes_tile619.coverage
    def coverage(s):
        s=old_coverage(s)
        return once(s,"c.label('coverage212');c.emit(0xa2,0,0)","""c.label('coverage212');lda(0x14d0);c.emit(0x89,1,0);c.branch(0xf0,'full632');c.emit(0xa2,144,0);c.jump('covered619')
 c.label('full632');c.emit(0xa2,0,0)""")
    with patch.object(nes_header546,'header',lambda s:extend(old_header(s))),patch.object(nes_tile619,'coverage',coverage):
        nes_raw624.build(out)
    path=out/'build.json'
    result=json.loads(path.read_text())
    result.update(candidate='seal632', seal_bytes=[24,168], diagnostic_context_B=10,
                  diagnostic_scratch_B=2, new_WRAM_B=12)
    path.write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);build(p.parse_args().out)
