# SPDX-License-Identifier: MIT
"""ACK-bound two-bank equality and literal OAM prefix on the actual 624 receiver."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
import nes_history547
import nes_header546
import nes_raw624
from nes_raw506 import once


def extend(s):
    s=once(s,"0xc9,9,0);c.branch(0x90,'packed_header181')","0xc9,10,0);c.branch(0x90,'packed_header181')")
    s=once(s," c.emit(0xc9,8,0);cond(0xf0,'repeat227')"," c.emit(0xc9,9,0);cond(0xf0,'reuse635')\n c.emit(0xc9,8,0);cond(0xf0,'repeat227')")
    s=once(s," c.label('service');","""
 c.label('reuse635');checkimm(0x1200,0x0409);checkimm(0x120a,0);checkimm(0x120c,116);checkimm(0x120e,0)
 checkimm(0x1086,0);checkimm(0x1088,0)
 lda(0x1034);c.absolute(0xcd,0x1032);cond(0xf0,'bad_packet')
 c.emit(0x0a,0x0a,0xaa)
 c.long(0xaf,0x400080);c.long(0x0f,0x400082);cond(0xf0,'bad_packet')
 for off in (0,2):
  c.long(0xaf,0x400080+off);c.absolute(0xdd,0x14d0+off);cond(0xd0,'bad_packet')
 # Compare both acknowledged palettes and the omitted OAM tail, word for
 # word. The two banks are symmetric, so X is a byte offset in bank 0.
 for start,end,name in ((0,512,'palette635'),(624,1056,'tail635')):
  c.emit(0xa2);c.word(start);c.label(name)
  for off in range(0,16,2):
   c.long(0xbf,0x7f6000+off);c.long(0xdf,0x7fe000+off);cond(0xd0,'bad_packet')
  c.emit(0x8a,0x18,0x69,16,0,0xaa,0x89,63,0);c.branch(0xd0,name+'next')
  call(c,'service');lda(0x1236);cond(0xd0,'stop_packet')
  c.label(name+'next');c.emit(0xe0);c.word(end);cond(0xd0,name)
 call(c,'service');lda(0x1236);cond(0xd0,'stop_packet')
 imm(112);sta(0x120c);c.jump('data')
 c.label('invalidate635')
 for i in range(0,8,2):c.absolute(0x9c,0x14d0+i)
 c.emit(0x60)
 c.label('service');""")
    s=once(s,"c.label('accepted');lda(0x1200);","""c.label('accepted');lda(0x1200);c.emit(0xc9,9,4);c.branch(0xd0,'ordinary635')
 imm(512);sta(0x1086);imm(544);sta(0x1088);c.jump('accepted194')
 c.label('ordinary635');lda(0x1200);""")
    s=once(s,"call(c,'maps181')","call(c,'invalidate635');call(c,'maps181')")
    s=once(s,"c.label('fail');sta(0x122a)","c.label('fail');call(c,'invalidate635');sta(0x122a)")
    s=once(s,"c.store(0x1236,1)","c.store(0x1236,1);c.emit(0xc2,0x20);call(c,'invalidate635');c.emit(0xe2,0x20)")
    return once(s,"c.absolute(0xee,0x1220);lda(0x1228)","""lda(0x1228);c.branch(0xd0,'nohistory635')
 lda(0x1200);c.emit(0xc9,3,0);c.branch(0xd0,'nohistory635')
 lda(0x1034);c.emit(0x0a,0x0a,0xaa)
 for off in (0,2):
  lda(0x1222+off);c.absolute(0x9d,0x14d0+off)
 c.label('nohistory635');c.absolute(0xee,0x1220);lda(0x1228)""")


def incremental(source):
    start=source.index(' # Compare both acknowledged palettes')
    end=source.index(" imm(112);sta(0x120c);c.jump('data')",start)
    source=source[:start]+"""
 c.label('remaining635')
 lda(0x14da);c.emit(0xc9,0xff,0xff);cond(0xf0,'bad_packet')
 c.emit(0xc9,0x20,4);c.branch(0xf0,'proven635')
 call(c,'service');lda(0x1236);cond(0xd0,'stop_packet')
 call(c,'compare635');c.jump('remaining635')
 c.label('proven635')
"""+source[end:]
    source=once(source," c.label('invalidate635')","""
 c.label('idle635')
 lda(0x1086);c.absolute(0x0d,0x1088);cond(0xd0,'return635')
 lda(0x14da);c.emit(0xc9,0x20,4);cond(0xb0,'return635')
 for base in (0x14d0,0x14d4):
  lda(base);c.absolute(0x0d,base+2);cond(0xf0,'return635')
 c.emit(0xe2,0x20);lda(0x6001);c.branch(0x30,'return8_635')
 lda(0x6000);c.emit(0x29,1);c.branch(0xd0,'return8_635');c.emit(0xc2,0x20)
 c.label('compare635');c.absolute(0xae,0x14da)
 for off in range(0,16,2):
  c.long(0xbf,0x7f6000+off);c.long(0xdf,0x7fe000+off);c.branch(0xd0,'unequal635')
 c.emit(0x8a,0x18,0x69,16,0,0xc9,0,2);c.branch(0xd0,'save635');imm(624)
 c.label('save635');sta(0x14da);c.emit(0x60)
 c.label('unequal635');imm(0xffff);sta(0x14da)
 c.label('return8_635');c.emit(0xc2,0x20);c.label('return635');c.emit(0x60)
 c.label('invalidate635')""")
    source=once(source,"call(c,'prefix523');c.jump('poll');c.label('head524')",
                "call(c,'prefix523');call(c,'idle635');c.jump('poll');c.label('head524')")
    return once(source,"c.label('begin');","c.label('begin');c.absolute(0x9c,0x14da);")


def build(out,short=False,idle=False):
    group=nes_history547.original_group
    def final_jobs(source,early):
        source=group(source,early)
        return once(source,';imm(size);sta(0x1104+slot)',"""
  lda(0x14d8);c.branch(0xf0,'full635_'+str(slot));imm(2 if slot==0 else 112);c.branch(0x80,'length635_'+str(slot))
  c.label('full635_'+str(slot));imm(size);c.label('length635_'+str(slot));sta(0x1104+slot)""")
    def receiver(source):
        source=extend(header(source))
        if idle:source=incremental(source)
        if short:
            source=once(source,"c.label('begin');","c.label('begin');c.absolute(0x9c,0x14d8);")
            source=once(source,'imm(512);sta(0x1086);imm(544)', 'imm(1);sta(0x14d8);imm(512);sta(0x1086);imm(544)')
            source=once(source,'range(0,8,2):c.absolute(0x9c,0x14d0+i)','range(0,10,2):c.absolute(0x9c,0x14d0+i)')
        return source
    header=nes_header546.header
    with patch.object(nes_header546,'header',receiver), patch.object(nes_history547,'original_group',final_jobs if short else group):
        nes_raw624.build(out)
    p=out/'build.json'
    j=json.loads(p.read_text());j.update(candidate='reuse635',receipt_WRAM_B=8,short_display=short,idle_proof=idle)
    p.write_text(json.dumps(j,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--short-display',action='store_true');p.add_argument('--idle-proof',action='store_true');a=p.parse_args();build(a.out,a.short_display,a.idle_proof)
