# SPDX-License-Identifier: MIT
"""Emit reusable 65816 WRAM-local diff; no MCU readback/cartridge save access.

Entry/exit native A16/X16, DBR=DP=0. Clobbers A/X/Y and DP40..6F.
Pending lengths1000[6], old1010[6], candidate1020, oldbase1022 (0/8000),
displayed1024(byte), status1025(byte), count1026, charged1028,payload102A,
budget1030. Output commands1100[32]*8: source16,dest16,size16,kind16.
Caller owns validated COMMIT/lease/ACK and must not publish rejected output.
No PPU writes, no memory bus mailbox or ACK transport in this routine.
"""
OFFSETS=(0,0x4000,0x5000,0x6000,0x6200,0x6500)
LIMITS=(16384,4096,4096,512,544,1121)
DESTS=(0,0x4000,0x8000,0,0,0)
KINDS=(0,0,0,1,2,3)

def call(c,label):
 c.emit(0x20,0,0);c.jumps.append((len(c.data)-2,label))

def emit(c,prefix='local165',service=None):
 """Optional service label called after <=64 compared bytes, A/X16 DB/DP0.
 It must preserve DP40..6F and return same widths. X/Y are saved by caller."""
 start=len(c.data);L=lambda n:prefix+'_'+n
 def label(n):c.label(L(n))
 def jump(n):c.jump(L(n))
 def cond(op,n):c.emit(op^0x20,3);jump(n) # opposite conditional skips JMP
 def jsr(n):call(c,L(n))
 def imm(v):c.emit(0xa9);c.word(v)
 def lda(a):c.absolute(0xad,a)
 def sta(a):c.absolute(0x8d,a)
 def zero(a):c.absolute(0x9c,a)
 # DP40 section table byte offset,42 current offset,44 size,46 oldsize,
 # 48..4A pending pointer,4C..4E old pointer,50 start,52 end,54 run,
 # 56 candidate base,58 old base,5A pending length,5C dirty offset,
 # 5E first-scene flag16,60 block bytes,62 comparison word scratch.
 label('entry');c.emit(0xe2,0x20);c.store(0x1025,1);c.emit(0xc2,0x20)
 zero(0x1026);zero(0x1028);zero(0x102a);zero(0x40)
 lda(0x1020);c.emit(0x89,0xff,0x7f);cond(0xd0,'invalid');lda(0x1020);sta(0x56)
 lda(0x1022);c.emit(0x89,0xff,0x7f);cond(0xd0,'invalid');lda(0x1022);sta(0x58)
 lda(0x1024);c.emit(0x29,0xff,0);sta(0x5e);cond(0xf0,'sizes')
 lda(0x56);c.emit(0xc5,0x58);cond(0xf0,'invalid')
 label('sizes');c.emit(0xa2,0,0)
 label('validate');c.absolute(0xbd,0x1000)
 # Compare pending/old sizes against an indexed ROM limit table.
 pos=len(c.data);c.long(0xdf,0);limit_fix=[pos+1];cond(0x90,'limit_ok');cond(0xd0,'invalid')
 label('limit_ok');c.absolute(0xbd,0x1010);pos=len(c.data);c.long(0xdf,0);limit_fix.append(pos+1);cond(0x90,'old_ok');cond(0xd0,'invalid')
 label('old_ok');c.emit(0xe8,0xe8,0xe0,12,0);cond(0xd0,'validate')
 lda(0x1000);cond(0xf0,'invalid');c.emit(0x29,15,0);cond(0xd0,'invalid')
 lda(0x1002);c.emit(0x29,31,0);cond(0xd0,'invalid')
 lda(0x1010);c.emit(0x29,15,0);cond(0xd0,'invalid')
 lda(0x1012);c.emit(0x29,31,0);cond(0xd0,'invalid')
 for addr,value in [(0x1004,4096),(0x1006,512),(0x1008,544)]:
  lda(addr);c.emit(0xc9);c.word(value);cond(0xd0,'invalid')
 lda(0x100a);cond(0xf0,'invalid')
 # Setup each region; source bank is always SNES WRAM7F.
 label('region');zero(0x42);zero(0x50);zero(0x52);zero(0x54);zero(0x60)
 c.emit(0xa6,0x40);c.absolute(0xbd,0x1000);sta(0x44);c.absolute(0xbd,0x1010);sta(0x46)
 pos=len(c.data);c.long(0xbf,0);offset_fix=[pos+1];c.emit(0x18,0x65,0x56);sta(0x48)
 pos=len(c.data);c.long(0xbf,0);offset_fix.append(pos+1);c.emit(0x18,0x65,0x58);sta(0x4c)
 c.emit(0xe2,0x20);c.store(0x4a,0x7f);c.store(0x4e,0x7f);c.emit(0xc2,0x20)
 lda(0x44);cond(0xf0,'next');lda(0x5e);cond(0xf0,'whole')
 c.emit(0xe0,6,0);cond(0x90,'word_loop')
 lda(0x44);c.emit(0xc5,0x46);cond(0xd0,'whole')
 # Palette/OAM/HDMA comparison is byte-exact, including odd-length HDMA.
 label('byte_loop');jsr('fast');cond(0x90,'byte_slow')
 lda(0x42);c.emit(0xc5,0x44);cond(0x90,'byte_loop');jump('next')
 label('byte_slow');c.emit(0xa4,0x42,0xe2,0x20,0xb7,0x48,0xd7,0x4c,0xc2,0x20);cond(0xd0,'whole')
 c.emit(0xe6,0x42,0xe6,0x60);jsr('yield');lda(0x42);c.emit(0xc5,0x44);cond(0x90,'byte_loop');jump('next')
 label('word_loop');jsr('fast');cond(0x90,'word_slow')
 lda(0x42);c.emit(0xc5,0x44);cond(0x90,'word_loop');jump('word_end')
 label('word_slow');c.emit(0xa4,0x42);lda(0x42);c.emit(0xc5,0x46);cond(0xb0,'dirty')
 c.emit(0xb7,0x48,0xd7,0x4c);cond(0xf0,'advance')
 label('dirty');lda(0x54);cond(0xf0,'new_run')
 lda(0x42);c.emit(0x38,0xe5,0x52,0xc9,33,0);cond(0x90,'extend')
 jsr('append');cond(0x90,'return');zero(0x54)
 label('new_run');lda(0x42);sta(0x50);imm(1);sta(0x54)
 label('extend');lda(0x42);c.emit(0x18,0x69,2,0);sta(0x52)
 label('advance');c.emit(0xe6,0x42,0xe6,0x42,0xe6,0x60,0xe6,0x60);jsr('yield')
 lda(0x42);c.emit(0xc5,0x44);cond(0x90,'word_loop')
 label('word_end');lda(0x54);cond(0xf0,'next');jsr('append');cond(0x90,'return');jump('next')
 label('whole');zero(0x50);lda(0x44);sta(0x52);jsr('append');cond(0x90,'return')
 label('next');c.emit(0xe6,0x40,0xe6,0x40);lda(0x40);c.emit(0xc9,12,0);cond(0x90,'region')
 c.emit(0xe2,0x20);c.store(0x1025,2);c.emit(0xc2,0x20);jump('return')
 label('invalid');c.emit(0xe2,0x20);c.store(0x1025,0xe1);c.emit(0xc2,0x20)
 label('return');c.emit(0x60)
 # Append at most32 commands, enforce visible-frame budget before any DMA.
 label('append');lda(0x1026);c.emit(0xc9,32,0);cond(0xb0,'overflow')
 lda(0x52);c.emit(0x38,0xe5,0x50);sta(0x5a)
 lda(0x1028);c.emit(0x18,0x65,0x5a,0x69,96,0);sta(0x5c)
 lda(0x5e);cond(0xf0,'admit');lda(0x5c);c.absolute(0xcd,0x1030);cond(0x90,'admit');cond(0xd0,'budget')
 label('admit');lda(0x5c);sta(0x1028);lda(0x102a);c.emit(0x18,0x65,0x5a);sta(0x102a)
 lda(0x1026);c.emit(0x0a,0x0a,0x0a,0xa8);lda(0x48);c.emit(0x18,0x65,0x50);c.absolute(0x99,0x1100)
 c.emit(0xa6,0x40);pos=len(c.data);c.long(0xbf,0);dest_fix=pos+1;c.emit(0x18,0x65,0x50);c.absolute(0x99,0x1102)
 lda(0x5a);c.absolute(0x99,0x1104);pos=len(c.data);c.long(0xbf,0);kind_fix=pos+1;c.absolute(0x99,0x1106)
 c.absolute(0xee,0x1026);c.emit(0x38,0x60)
 label('overflow');c.emit(0xe2,0x20);c.store(0x1025,0xe2);c.emit(0xc2,0x20,0x18,0x60)
 label('budget');c.emit(0xe2,0x20);c.store(0x1025,0xe3);c.emit(0xc2,0x20,0x18,0x60)
 label('yield');lda(0x60);c.emit(0xc9,64,0);cond(0x90,'yield_return');zero(0x60)
 if service:
  c.emit(0xda,0x5a);call(c,service);c.emit(0x7a,0xfa)
 label('yield_return');c.emit(0x60)
 # Equal 64-byte blocks use DBR=7F and eight unrolled word comparisons.
 # Both candidates have identical relative layouts, so comparison is symmetric.
 # Tail/growth and dirty blocks return to the exact byte/word path above.
 label('fast');lda(0x42);c.emit(0x29,63,0);cond(0xd0,'fast_no')
 for a in [0x44,0x46]:
  lda(a);c.emit(0x38,0xe5,0x42);cond(0x90,'fast_no');c.emit(0xc9,64,0);cond(0x90,'fast_no')
 lda(0x48);c.emit(0x29,0xff,0x7f,0x18,0x65,0x42,0xaa,0xa0,4,0)
 c.emit(0x8b,0xe2,0x20,0xa9,0x7f,0x48,0xab,0xc2,0x20)
 label('fast_words')
 for i in range(8):
  c.absolute(0xbd,i*2);c.absolute(0xdd,0x8000+i*2);c.branch(0xd0,L('fast_dirty'))
 c.emit(0x8a,0x18,0x69,16,0,0xaa)
 c.emit(0x88);c.branch(0xd0,L('fast_words'));c.emit(0xab)
 lda(0x42);c.emit(0x18,0x69,64,0);sta(0x42);imm(64);sta(0x60);jsr('yield');c.emit(0x38,0x60)
 label('fast_dirty');c.emit(0xab)
 label('fast_no');c.emit(0x18,0x60)
 for values,fixes in [(LIMITS,limit_fix),(OFFSETS,offset_fix),(DESTS,[dest_fix]),(KINDS,[kind_fix])]:
  address=c.base+len(c.data)
  for pos in fixes:c.data[pos:pos+3]=address.to_bytes(3,'little')
  for value in values:c.word(value)
 return dict(entry=L('entry'),code_bytes=len(c.data)-start,scratch=[0x40,0x6f],command_bytes=256,wrambank=0x7f)

def emit_upload(c,prefix='upload165'):
 """Consume only the local routine's READY list. Entry A/X16 DB/DP0.
 Caller sets native PPU layout, keeps first scene blank and owns bank7F.
 Visible updates wait for a fresh vblank. status3 means local DMA finished,
 NOT a transport ACK; caller must publish token/gen and preserve ownership.
 """
 start=len(c.data);L=lambda n:prefix+'_'+n
 def label(n):c.label(L(n))
 def jump(n):c.jump(L(n))
 def cond(op,n):c.emit(op^0x20,3);jump(n)
 label('entry');c.emit(0xe2,0x20);c.absolute(0xad,0x1025);c.emit(0xc9,2);cond(0xd0,'return')
 c.absolute(0xad,0x1024);cond(0xf0,'blank_ready')
 label('active');c.absolute(0xad,0x4212);cond(0x30,'active')
 label('blank');c.absolute(0xad,0x4212);cond(0x10,'blank')
 label('blank_ready');c.store(0x420c,0);c.emit(0xc2,0x20)
 c.absolute(0xad,0x1026);c.emit(0x0a,0x0a,0x0a);c.absolute(0x8d,0x1070);c.emit(0xa2,0,0)
 label('loop');c.absolute(0xec,0x1070);cond(0xb0,'finish')
 c.absolute(0xbd,0x1106);cond(0xf0,'vram');c.emit(0xc9,1,0);cond(0xf0,'cgram');c.emit(0xc9,2,0);cond(0xf0,'oam');jump('advance')
 label('vram');c.absolute(0xbd,0x1102);c.emit(0x4a);c.absolute(0x8d,0x2116)
 c.emit(0xe2,0x20);c.store(0x4300,1);c.store(0x4301,0x18);jump('transfer')
 label('cgram');c.emit(0xe2,0x20);c.store(0x2121,0);c.store(0x4300,2);c.store(0x4301,0x22);jump('transfer')
 label('oam');c.emit(0xe2,0x20);c.store(0x2102,0);c.store(0x2103,0);c.store(0x4300,0);c.store(0x4301,4)
 label('transfer');c.emit(0xc2,0x20);c.absolute(0xbd,0x1100);c.absolute(0x8d,0x4302)
 c.absolute(0xbd,0x1104);c.absolute(0x8d,0x4305);c.emit(0xe2,0x20);c.store(0x4304,0x7f);c.store(0x420b,1);c.emit(0xc2,0x20)
 label('advance');c.emit(0x8a,0x18,0x69,8,0,0xaa);jump('loop')
 label('finish');c.emit(0xe2,0x20)
 c.absolute(0xad,0x1024);cond(0xd0,'scroll')
 label('reveal_active');c.absolute(0xad,0x4212);cond(0x30,'reveal_active')
 label('reveal_blank');c.absolute(0xad,0x4212);cond(0x10,'reveal_blank')
 label('scroll')
 for source,port in [(0x102c,0x210d),(0x102e,0x210e)]:
  for a in [source,source+1]:c.absolute(0xad,a);c.absolute(0x8d,port)
 for a,v in [(0x4310,3),(0x4311,0x0d),(0x4312,0),(0x4314,0x7f)]:c.store(a,v)
 c.absolute(0xad,0x1021);c.emit(0x18,0x69,0x65);c.absolute(0x8d,0x4313)
 c.store(0x420c,2);c.store(0x2100,15);c.store(0x1025,3)
 label('return');c.emit(0xc2,0x20,0x60)
 return dict(entry=L('entry'),code_bytes=len(c.data)-start)
