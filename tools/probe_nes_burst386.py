# SPDX-License-Identifier: MIT
"""Actual65816 adaptive sparse/column/dense WRAM-first map DMA candidate.

Initial target-bank map/OAM images are explicit prior-frame fixtures. This is
not a cold initialization,fullresident firmware or independent hardware PPU
receipt implementation. Existing read receipts mean WRAM storage acceptance;
the actual CPU withholds finalACK until all PPU jobs have completed.
"""
import argparse,csv,json,os,struct,subprocess
from collections import OrderedDict
from pathlib import Path
from build_nes_trace_replay import Code
import probe_nes_display266 as display
import probe_nes_vblank381 as commit
from probe_nes_arm264 import plans
from nes_delta231 import ROOT,BASE,sha


def rom(d):
 c=Code(0x8000)
 def lda(a):c.absolute(0xad,a)
 def sta(a):c.absolute(0x8d,a)
 def far(op,a):c.emit(op,a&255,(a>>8)&255,a>>16)
 def cond(op,label):c.emit(op^0x20,3);c.jump(label)
 def word(a,n):c.emit(0xc2,0x20,0xa9,n&255,n>>8);sta(a);c.emit(0xe2,0x20)
 def fault():lda(0x6001);c.emit(0x29,0xc0);cond(0xd0,'abort383')
 def job():
  c.emit(0xc2,0x20);c.absolute(0xae,0x22);c.emit(0xe0,0,0xb0);cond(0xb0,'abort16_383')
  for source,offset in ((0x28,0),(0x20,2),(0x26,4)):
   lda(source);far(0x9f,0x7e0000+offset)
  c.emit(0xe2,0x20)
  for source,offset in ((0x2a,6),(0x2b,7),(0x60,8),(0x61,9),(0x62,10),(0x63,11),(0x2e,12)):
   lda(source);far(0x9f,0x7e0000+offset)
  c.emit(0xc2,0x20);lda(0x22);c.emit(0x18,0x69,16,0);sta(0x22);c.emit(0xe2,0x20)
 c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b,0xe2,0x20)
 for a,v in ((0x4200,0),(0x420c,0),(0x4201,255),(0x2100,15),(0x10,0),(0x11,0),(0x12,0),(0x13,0),(0x2c,0),(0x2d,0),(0x2e,0),(0x2f,0)):
  c.store(a,v)
 word(0x16,0x8000);word(0x22,0xa000);word(0x24,0xa000);word(0x88,0);word(0x8a,0);c.store(0x2e,0x80)
 c.label('next383');fault();lda(0x6054);cond(0xd0,'ready383')
 lda(0x6000);cond(0xd0,'ordinary383');lda(0x6040);cond(0xf0,'next383')
 c.emit(0xa2,0,0)
 c.label('typed_desc383');c.absolute(0xbd,0x6041);c.absolute(0x9d,0x30);c.emit(0xe8,0xe0,11,0);c.branch(0xd0,'typed_desc383')
 for i in range(4):lda(0x37+i);sta(0x60+i)
 lda(0x30);c.emit(0x29,4);c.branch(0xf0,'bank0_383');c.store(0x2d,1);c.jump('typed_length383')
 c.label('bank0_383');c.store(0x2d,0)
 c.label('typed_length383');c.emit(0xc2,0x20);lda(0x31);sta(0x26);cond(0xf0,'abort16_383');c.emit(0xe2,0x20)
 lda(0x30);c.emit(0x29,2);cond(0xd0,'map383')
 # Tile payload occupies bounded append-only WRAM,not the live PPU bank.
 c.emit(0xc2,0x20);lda(0x16);sta(0x20);c.emit(0x18);c.absolute(0x6d,0x26);cond(0xb0,'abort16_383');c.emit(0xc9,1,0xa0);cond(0xb0,'abort16_383');sta(0x16);c.emit(0xe2,0x20)
 lda(0x30);c.emit(0x29,1);c.branch(0xd0,'obj383')
 c.emit(0xc2,0x20);lda(0x33);c.emit(0x0a,0x0a,0x0a);sta(0x28);c.emit(0xe2,0x20);lda(0x2d);c.branch(0xf0,'tile_base_done383')
 c.emit(0xc2,0x20);lda(0x28);c.emit(0x18,0x69,0,0x60);sta(0x28);c.emit(0xe2,0x20);c.jump('tile_base_done383')
 c.label('obj383');c.emit(0xc2,0x20);lda(0x33);c.emit(0x0a,0x0a,0x0a,0x0a,0x18,0x69,0,0x20);sta(0x28);c.emit(0xe2,0x20);lda(0x2d);c.branch(0xf0,'tile_base_done383')
 c.emit(0xc2,0x20);lda(0x28);c.emit(0x18,0x69,0,0x20);sta(0x28);c.emit(0xe2,0x20)
 c.label('tile_base_done383');c.store(0x2a,0);c.store(0x2b,0x7e);c.store(0x2c,0);c.jump('copy383')
 c.label('map383');c.emit(0xc2,0x20);lda(0x33);c.emit(0x0a,0x18,0x69,0,0xc0);sta(0x20);c.emit(0xe2,0x20);lda(0x2d);c.branch(0xf0,'map_base383')
 c.emit(0xc2,0x20);lda(0x20);c.emit(0x18,0x69,0,0x10);sta(0x20);c.emit(0xe2,0x20)
 c.label('map_base383');c.emit(0xc2,0x20);c.absolute(0xee,0x88);lda(0x8a);c.emit(0x18);c.absolute(0x6d,0x26);sta(0x8a);c.emit(0xe2,0x20);c.store(0x10,1);c.store(0x2b,0x7e);c.store(0x2c,2)
 c.emit(0xc2,0x20);lda(0x33);c.emit(0x18,0x69,0,0x30);sta(0x28);c.emit(0xe2,0x20);lda(0x2d);c.branch(0xf0,'map_target386')
 c.emit(0xc2,0x20);lda(0x28);c.emit(0x18,0x69,0,0x20);sta(0x28);c.emit(0xe2,0x20)
 c.label('map_target386');c.store(0x2a,3);c.jump('copy383')
 c.label('ordinary383');c.emit(0xa2,0,0)
 c.label('ordinary_desc383');c.absolute(0xbd,0x6060);c.absolute(0x9d,0x40);c.emit(0xe8,0xe0,9,0);c.branch(0xd0,'ordinary_desc383')
 for i in range(4):lda(0x6048+i);sta(0x60+i)
 lda(0x40);cond(0xd0,'abort383');lda(0x41);c.emit(0xc9,3);c.branch(0xf0,'cg383');c.emit(0xc9,4);cond(0xd0,'abort383');c.store(0x12,1);c.jump('ordinary_copy383')
 c.label('cg383');c.store(0x11,1)
 c.label('ordinary_copy383');lda(0x48);sta(0x2d);c.emit(0xc2,0x20);lda(0x42);sta(0x20);lda(0x44);sta(0x26);cond(0xf0,'abort16_383');c.emit(0xe2,0x20);c.store(0x2b,0x7f);c.store(0x2c,1)
 c.label('copy383');fault();c.emit(0xc2,0x20);lda(0x20);sta(0x2181);lda(0x26);sta(0x4305);c.emit(0xe2,0x20)
 lda(0x2b);c.emit(0x29,1);sta(0x2183)
 for a,v in ((0x4300,0),(0x4301,0x80),(0x4302,0),(0x4303,8),(0x4304,0x40),(0x420b,1)):c.store(a,v)
 lda(0x2c);c.emit(0xc9,1);c.branch(0xf0,'stage_done383');job()
 c.label('stage_done383');fault()
 for i in range(4):lda(0x60+i);sta(0x604c+i)
 lda(0x2c);c.emit(0xc9,1);c.branch(0xf0,'ordinary_ack383');c.store(0x6050,0xa5);c.jump('next383')
 c.label('ordinary_ack383');c.store(0x6059,0xa5);c.jump('next383')
 c.label('ready383');fault()
 # Read/seal the exact display view before choosing the atomic PPU window.
 c.emit(0xa2,0,0);c.label('view383');c.absolute(0xbd,0x6070);c.absolute(0x9d,0x1000);c.emit(0xe8,0xe0,12,0);c.branch(0xd0,'view383')
 # Derive bounds only from received map jobs,after all source storage.
 # Two32x32screens have64columns. min/max use128B at7EF000,not64B.
 lda(0x1000);c.branch(0xf0,'valid_bank0_386');far(0xaf,0x7ef080);c.emit(0x29,2);c.branch(0x80,'valid_test386')
 c.label('valid_bank0_386');far(0xaf,0x7ef080);c.emit(0x29,1)
 c.label('valid_test386');cond(0xf0,'abort383')
 lda(0x10);cond(0xf0,'map_job_done383')
 # Bounded low-change policy avoids a full64column analysis for<=7ranges/128B.
 # This is a safe sparse shortcut,not a claim of globally minimal DMA cost.
 c.emit(0xc2,0x20);lda(0x88);c.emit(0xc9,8,0);c.branch(0xb0,'full_analyze386');lda(0x8a);c.emit(0xc9,129,0);c.branch(0xb0,'full_analyze386')
 c.emit(0x0a,0x0a,0x0a);sta(0x68);lda(0x88);c.emit(0xeb);sta(0x6c);c.emit(0x0a,0x0a,0x18);c.absolute(0x6d,0x6c);c.emit(0x18);c.absolute(0x6d,0x68);sta(0x68);word(0x6a,65535);word(0x7a,0);c.jump('strategy386')
 c.label('full_analyze386')
 c.emit(0xc2,0x20,0xa2,0,0,0xa9,32,0)
 c.label('bounds_init386');far(0x9f,0x7ef000);c.emit(0xe8,0xe8,0xe0,128,0);c.branch(0xd0,'bounds_init386')
 word(0x66,0xa000);word(0x68,0);word(0x6a,0);word(0x6c,0);word(0x7a,0)
 c.label('range386');c.emit(0xe2,0x20);fault();c.emit(0xc2,0x20);c.absolute(0xae,0x66);c.absolute(0xec,0x22);cond(0xf0,'ranges_done386');c.emit(0xe2,0x20);far(0xbf,0x7e0006);c.emit(0xc9,3);cond(0xd0,'range_next386')
 c.emit(0xc2,0x20);far(0xbf,0x7e0000);c.emit(0x29,255,7);sta(0x70);far(0xbf,0x7e0004);c.emit(0x4a);sta(0x72)
 # Saturate sparse budget instead of wrapping an admission estimate.
 far(0xbf,0x7e0004);c.emit(0x0a,0x0a,0x0a,0x18,0x69,0,5);c.branch(0xb0,'saturate386');c.emit(0x18);c.absolute(0x6d,0x68);c.branch(0x90,'sparse_cost386')
 c.label('saturate386');c.emit(0xa9,255,255)
 c.label('sparse_cost386');sta(0x68)
 c.label('word386')
 lda(0x70);c.emit(0x29,31,0,0x0a);sta(0x74);lda(0x70);c.emit(0x29,0,4,0x4a,0x4a,0x4a,0x4a);c.absolute(0x0d,0x74);c.emit(0xaa)
 lda(0x70);c.emit(0x4a,0x4a,0x4a,0x4a,0x4a,0x29,31,0,0xe2,0x20);sta(0x75)
 far(0xdf,0x7ef000);c.branch(0xb0,'min_done386');far(0x9f,0x7ef000)
 c.label('min_done386');lda(0x75);far(0xdf,0x7ef001);c.branch(0x90,'max_done386');far(0x9f,0x7ef001)
 c.label('max_done386');c.emit(0xc2,0x20);c.absolute(0xee,0x70);c.absolute(0xce,0x72);cond(0xd0,'word386')
 c.label('range_next386');c.emit(0xc2,0x20);lda(0x66);c.emit(0x18,0x69,16,0);sta(0x66);c.jump('range386')
 c.label('ranges_done386');word(0x76,0)
 c.label('column_cost386');c.emit(0xc2,0x20);c.absolute(0xae,0x76);far(0xbf,0x7ef000);c.emit(0x29,255,0,0xc9,32,0);c.branch(0xb0,'column_cost_next386');sta(0x70)
 far(0xbf,0x7ef001);c.emit(0x29,255,0,0x38);c.absolute(0xed,0x70);c.emit(0x1a,0x0a,0x0a,0x0a,0x0a,0x18,0x69,0,5,0x18);c.absolute(0x6d,0x6a);c.branch(0x90,'column_sum386');c.emit(0xa9,255,255)
 c.label('column_sum386');sta(0x6a)
 c.label('column_cost_next386');c.absolute(0xee,0x76);c.absolute(0xee,0x76);lda(0x76);c.emit(0xc9,128,0);c.branch(0xd0,'column_cost386')
 # Strategy0=sparse,1=column,2=dense;ties favor sparse/no gather.
 lda(0x68);sta(0x6c);lda(0x6a);c.absolute(0xcd,0x6c);c.branch(0xb0,'dense_compare386');sta(0x6c);word(0x7a,1)
 c.label('dense_compare386');c.emit(0xc2,0x20);lda(0x6c);c.emit(0xc9,0,0x85);c.branch(0x90,'strategy386');word(0x7a,2)
 c.label('strategy386');word(0x66,0xa000);word(0x84,0xa000);c.store(0x86,0x7e)
 # Compact obsolete map records before VBlank;do not charge hidden skip loops.
 c.label('convert386');c.emit(0xc2,0x20);c.absolute(0xae,0x66);c.absolute(0xec,0x22);cond(0xf0,'convert_done386');c.emit(0xe2,0x20);far(0xbf,0x7e0006);c.emit(0xc9,3);c.branch(0xd0,'copy_job386');lda(0x7a);cond(0xd0,'convert_next386');c.emit(0xa9,0);far(0x9f,0x7e0006)
 c.label('copy_job386');c.emit(0xc2,0x20,0xa0,0,0)
 for off in range(0,16,2):
  far(0xbf,0x7e0000+off);c.emit(0x97,0x84,0xc8,0xc8)
 lda(0x84);c.emit(0x18,0x69,16,0);sta(0x84)
 c.label('convert_next386');c.emit(0xc2,0x20);lda(0x66);c.emit(0x18,0x69,16,0);sta(0x66);c.jump('convert386')
 c.label('convert_done386');lda(0x84);sta(0x22);c.emit(0xe2,0x20);lda(0x7a);cond(0xf0,'map_job_done383');c.emit(0xc9,2);cond(0xd0,'columns386')
 word(0x20,0xc000);word(0x28,0x3000);lda(0x1000);c.branch(0xf0,'dense_job386');word(0x20,0xd000);word(0x28,0x5000)
 c.label('dense_job386');word(0x26,4096);c.store(0x2a,0);c.store(0x2b,0x7e);job();c.jump('map_job_done383')
 c.label('columns386');word(0x74,0xe000);word(0x76,0);word(0x78,0xc000);lda(0x1000);c.branch(0xf0,'column_loop386');word(0x78,0xd000)
 c.label('column_loop386');c.emit(0xe2,0x20);fault();c.emit(0xc2,0x20);c.absolute(0xae,0x76);far(0xbf,0x7ef000);c.emit(0x29,255,0,0xc9,32,0);cond(0xb0,'column_next386');sta(0x70)
 far(0xbf,0x7ef001);c.emit(0x29,255,0,0x38);c.absolute(0xed,0x70);c.emit(0x1a);sta(0x72);c.emit(0x0a);sta(0x26)
 lda(0x70);c.emit(0x0a,0x0a,0x0a,0x0a,0x0a);sta(0x70);lda(0x76);c.emit(0x4a,0x29,31,0);c.absolute(0x0d,0x70);sta(0x70);lda(0x76);c.emit(0x29,64,0,0x0a,0x0a,0x0a,0x0a);c.absolute(0x0d,0x70);sta(0x70)
 c.emit(0x18,0x69,0,0x30);sta(0x28);c.emit(0xe2,0x20);lda(0x1000);c.branch(0xf0,'column_dest386');c.emit(0xc2,0x20);lda(0x28);c.emit(0x18,0x69,0,0x20);sta(0x28);c.emit(0xe2,0x20)
 c.label('column_dest386');c.emit(0xc2,0x20);lda(0x70);c.emit(0x0a,0x18);c.absolute(0x6d,0x78);sta(0x80);lda(0x74);sta(0x20);c.absolute(0xae,0x74);c.emit(0xe2,0x20);c.store(0x82,0x7e);c.emit(0xc2,0x20,0xa0,0,0)
 c.label('gather386');c.emit(0xb7,0x80);far(0x9f,0x7e0000);c.emit(0xe8,0xe8,0x98,0x18,0x69,64,0,0xa8);c.absolute(0xce,0x72);c.branch(0xd0,'gather386');c.absolute(0x8e,0x74);c.emit(0xe2,0x20)
 c.store(0x2a,0);c.store(0x2b,0x7e);c.store(0x2e,0x81);job()
 c.label('column_next386');c.emit(0xc2,0x20);c.absolute(0xee,0x76);c.absolute(0xee,0x76);lda(0x76);c.emit(0xc9,128,0);cond(0x90,'column_loop386');c.emit(0xe2,0x20)
 c.label('map_job_done383')
 for flag,length,source,kind in ((0x11,512,0x6000,1),(0x12,544,0x6200,2)):
  label='ordinary_job'+str(flag);lda(flag);cond(0xf0,label);word(0x20,source);lda(0x1000);c.branch(0xf0,label+'_bank');word(0x20,source+0x8000)
  c.label(label+'_bank');word(0x26,length);word(0x28,0);c.store(0x2a,kind);c.store(0x2b,0x7f);job();c.label(label)
 # Reserve3328clocks for commit/control;view reads happen before the window.
 # All VRAM jobs precede CGRAM/OAM. Configure their common DMA mode/bank once
 # outside VBlank rather than rebuilding it for every small range.
 for a,v in ((0x2115,0x80),(0x4300,1),(0x4301,0x18),(0x4304,0x7e)):c.store(a,v)
 # Job cap is checked before
 # any PPU write. The per-job setup bound is measured/checked by native tests.
 word(0x18,3328);c.emit(0xc2,0x20);c.absolute(0xae,0x24)
 c.label('budget383');c.absolute(0xec,0x22);c.branch(0xf0,'budget_done383');far(0xbf,0x7e0004);c.emit(0x0a,0x0a,0x0a,0x18,0x69,0,5);cond(0xb0,'abort16_383');c.emit(0x18);c.absolute(0x6d,0x18);cond(0xb0,'abort16_383');c.emit(0xc9,0xd1,0xbf);cond(0xb0,'abort16_383');sta(0x18);c.emit(0x8a,0x18,0x69,16,0,0xaa);c.jump('budget383')
 c.label('budget_done383');lda(0x18);c.emit(0xc9,0x21,0x4e);c.branch(0x90,'cut246383');c.emit(0xc9,0x31,0x75);c.branch(0x90,'cut238383');c.emit(0xc9,0x41,0x9c);c.branch(0x90,'cut230383');word(0x1a,225);c.jump('window383');c.label('cut230383');word(0x1a,230);c.jump('window383')
 c.label('cut246383');word(0x1a,246);c.jump('window383');c.label('cut238383');word(0x1a,238)
 c.label('window383');c.emit(0xe2,0x20);fault();lda(0x4212);c.branch(0x10,'window383')
 lda(0x213f);lda(0x2137);lda(0x213d);sta(0x14);c.store(0x15,0);lda(0x213d);c.emit(0xc2,0x20,0x29,1,0,0xeb);c.absolute(0x0d,0x14);c.emit(0xc9,225,0);c.branch(0x90,'window383');c.absolute(0xcd,0x1a);c.branch(0x90,'flush383');c.branch(0xf0,'flush383')
 c.emit(0xe2,0x20);c.label('late383');fault();lda(0x4212);c.branch(0x30,'late383');c.jump('window383')
 c.label('flush383');c.emit(0xe2,0x20)
 c.label('job383');fault();c.emit(0xc2,0x20);c.absolute(0xae,0x24);c.absolute(0xec,0x22);cond(0xf0,'display_entry383')
 for offset,target in ((2,0x4302),(4,0x4305)):
  far(0xbf,0x7e0000+offset);sta(target)
 c.emit(0xe2,0x20);far(0xbf,0x7e0006);c.branch(0xf0,'vram383');c.emit(0xc9,1);c.branch(0xf0,'cgram383')
 c.emit(0xc2,0x20);far(0xbf,0x7e0000);sta(0x2102);c.emit(0xe2,0x20);c.store(0x4300,0);c.store(0x4301,4);c.store(0x4304,0x7f);c.jump('ppu383')
 c.label('cgram383');far(0xbf,0x7e0000);sta(0x2121);c.store(0x4300,2);c.store(0x4301,0x22);c.store(0x4304,0x7f);c.jump('ppu383')
 c.label('vram383');far(0xbf,0x7e000c);sta(0x2115);c.emit(0xc2,0x20);far(0xbf,0x7e0000);sta(0x2116);c.emit(0xe2,0x20)
 c.label('ppu383');fault();c.store(0x420b,1);c.emit(0xea)
 c.label('ppu_done383');c.emit(0xc2,0x20);lda(0x24);c.emit(0x18,0x69,16,0);sta(0x24);c.emit(0xe2,0x20);c.jump('job383')
 c.label('display_entry383');c.emit(0xe2,0x20);fault();lda(0x4212);cond(0x10,'abort383');c.jump('display383')
 c.label('abort16_383');c.emit(0xe2,0x20)
 c.label('abort383');c.emit(0xa9,0);far(0x8f,0x7ef080);c.store(0x420c,0);c.store(0x2100,0x80);c.store(0x606f,0xee);c.label('halt383');c.branch(0x80,'halt383')
 c.labels['display383']=0;prefix=c.finish();offset=len(prefix)
 original=display.Code
 try:
  display.Code=lambda origin:original(origin+offset)
  body=commit.rom(d);labels=json.loads((d/'labels.json').read_text())
 finally:display.Code=original
 # Enter381 after its view loop. Its preamble and forcedblank are unreachable.
 c.labels['display383']=labels['safe380_apply'];prefix=c.finish();suffix=(d/'display.sfc').read_bytes()[:body]
 image=bytearray([255])*32768;image[:offset]=prefix;image[offset:offset+body]=suffix
 image[0x7fc0:0x7fd5]=b'NES386 ADAPTIVE DMA  ';image[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0])
 for p in range(0x7fe0,0x8000,2):struct.pack_into('<H',image,p,0x8000)
 checksum=sum(image)&65535;struct.pack_into('<HH',image,0x7fdc,checksum^65535,checksum)
 (d/'spool.sfc').write_bytes(image);all_labels=dict(c.labels,commit383_active=labels['active']);(d/'spool-labels.json').write_text(json.dumps(all_labels,indent=2)+'\n')
 return offset+body,all_labels


def fixtures(frame):
 ref=BASE/'probes/nes-present378/control02';events=list(csv.reader((ref/'joint-events.csv').read_text().splitlines()));groups=OrderedDict()
 for x in events:
  if x[:2]==['read336',str(frame)]:groups.setdefault(int(x[2]),[]).append(x)
 bank=(frame-905)%2;result=[]
 for token,rows in groups.items():
  op,section,pos=map(int,rows[0][3:6]);data=bytes(int(x[7]) for x in rows)
  if op not in (7,12,14) and section not in (3,4):continue
  assert [int(x[6]) for x in rows]==list(range(len(data)))
  if op in (7,12,14):
   ismap=op in (12,14);slot=pos//(2 if ismap else 16 if section==0 else 32)
   flags=(bank<<2)|(2 if ismap else section);desc=bytes([flags])+struct.pack('<HHHI',len(data),slot,frame-904,token)
   target=(0x3000+bank*0x2000+slot if ismap else (bank*0x6000+slot*8 if section==0 else 0x2000+bank*0x2000+slot*16))
   result.append(dict(typed=True,descriptor=desc.hex(),data=data.hex(),token=token,kind=0,target=target,bank=bank))
  else:
   target=(0x6000 if section==3 else 0x6200)+bank*0x8000+pos
   desc=bytes([0,section])+struct.pack('<HHH',target,len(data),pos//2)+bytes([bank])
   result.append(dict(typed=False,descriptor=desc.hex(),data=data.hex(),token=token,kind=section-2,target=pos//2,bank=bank))
 return result


def current_view(frame):
 ref=BASE/'probes/nes-present378/control02';packets=[bytes.fromhex(t['tx']) for t in json.loads((ref/f'arm{frame}.json').read_text())['transfers']]
 manifests=[p for p in packets if p[:2]==b'\xe1\x0f'];assert len(manifests)==1
 fields=manifests[0][17:41];assert len(fields)==24
 certificate=bytes.fromhex((ref/f'prelude{frame}.hex').read_text())
 view=bytes([(frame-905)%2,fields[18],fields[22]])+certificate[30:35]+fields[12:16]
 assert len(view)==12 and view[1:3]==bytes([24,2]);return view


LUA=r'''
local raw=assert(io.open(OUT..'/fixture.json','r')):read('*a')
-- Tables are emitted as Lua literals by the Python driver;no JSON dependency.
local FINAL_TOKEN=0;for _,j in ipairs(JOBS)do if j.typed and tonumber(j.descriptor:sub(1,2),16)%4>=2 then FINAL_TOKEN=j.token end end
local at=1;local reads=0;local staged=0;local jobdone=0;local ppu_start=nil;local ppu_end=nil;local viewreads=0;local ack={};local faultreads=0
local bus=assert(io.open(OUT..'/events.csv','w'));local timings=assert(io.open(OUT..'/timings.csv','w'));timings:write('phase,case,clock,scanline\n')
local function state()return emu.getState()end
local function note(op,a,v)local s=state();bus:write(string.format('%d,%d,%d,%d,%d,%d\n',at,op,a,v or 0,s.masterClock,s['ppu.scanline']));bus:flush();return v end
local function mark(kind)local s=state();timings:write(string.format('%s,%d,%d,%d\n',kind,at,s.masterClock,s['ppu.scanline']));timings:flush()end
local function bytes(s)local t={};for b in s:gmatch('%x%x')do t[#t+1]=tonumber(b,16)end;return t end
for _,j in ipairs(JOBS)do j.desc=bytes(j.descriptor);j.payload=bytes(j.data)end
for i,b in ipairs(bytes(INITMAP))do emu.write(0xc000+BANK*0x1000+i-1,b,emu.memType.snesWorkRam)end
for i,b in ipairs(bytes(INITMAP))do emu.write(0x6000+BANK*0x4000+i-1,b,emu.memType.snesVideoRam)end
for i,b in ipairs(bytes(INITOAM))do emu.write(0x16200+BANK*0x8000+i-1,b,emu.memType.snesWorkRam)end
emu.write(0xf080,3,emu.memType.snesWorkRam) -- Explicit warm-cache admission fixture;no cold loader.
for _,a in ipairs({0x16500,0x17161,0x17203,0x1e500,0x1f1b2,0x1f203})do emu.write(a,0,emu.memType.snesWorkRam)end
emu.addMemoryCallback(function(a,v)
 local j=JOBS[at]
 if a==0x6001 then faultreads=faultreads+1;return note(0,a,(STOP and staged>=1) and 0x80 or 0)end
 if a==0x6054 then return note(0,a,j and 0 or 1)end
 if a>=0x6070 and a<=0x607b then viewreads=viewreads+1;assert(a==0x6070+viewreads-1);return note(0,a,VIEW[viewreads])end
 if a==0x6000 then return note(0,a,j and not j.typed and 1 or 0)end
 if a==0x6040 then return note(0,a,j and j.typed and 1 or 0)end
 if a>=0x6048 and a<=0x604b then return note(0,a,math.floor((j and j.token or FINAL_TOKEN)/2^(8*(a-0x6048)))%256)end
 if a>=0x6041 and a<=0x6047 then assert(j and j.typed);return note(0,a,j.desc[a-0x6041+1])end
 if a>=0x6060 and a<=0x6068 then assert(j and not j.typed);return note(0,a,j.desc[a-0x6060+1])end
 return v
end,emu.callbackType.read,0x6000,0x607b)
emu.addMemoryCallback(function(a,v)local j=assert(JOBS[at]);assert(a==0x400800+reads);reads=reads+1;return note(0,a,assert(j.payload[reads]))end,emu.callbackType.read,0x400800,0x4017ff)
emu.addMemoryCallback(function(a,v)
 note(1,a,v)
 if a>=0x604c and a<=0x604f then ack[a-0x604c]=v;return end
 if a==0x6050 or a==0x6059 then
  local j=assert(JOBS[at]);assert(reads==#j.payload and v==0xa5);for i=0,3 do assert(ack[i]==math.floor(j.token/2^(8*i))%256)end
  assert(a==(j.typed and 0x6050 or 0x6059));assert(not ppu_start,'PPU before all source staging');mark('stored');at=at+1;reads=0;ack={};staged=staged+1
 elseif a==0x6058 then
  assert(v==0x5a and not STOP and staged==#JOBS and jobdone>0 and viewreads==12 and ppu_end,'early finalACK')
  local s=state();assert(s['ppu.scanline']>=225 and math.floor(s.masterClock/357368)==math.floor(ppu_start/357368),'atomic PPU/display frame')
  for i=0,3 do assert(ack[i]==math.floor(FINAL_TOKEN/2^(8*i))%256,'final map token')end
  local expected=bytes(EXPECTMAP);for i,b in ipairs(expected)do assert(emu.read(0x6000+BANK*0x4000+i-1,emu.memType.snesVideoRam)==b,'full mapVRAM')end
  for _,j in ipairs(JOBS)do if j.typed and j.desc[1]%4<2 then for i,b in ipairs(j.payload)do assert(emu.read(j.target*2+i-1,emu.memType.snesVideoRam)==b,'tileVRAM')end end end
  expected=bytes(EXPECTOAM);for i,b in ipairs(expected)do assert(emu.read(i-1,emu.memType.snesSpriteRam)==b,'OAM')end
  local out=assert(io.open(OUT..'/cpu-result.json','w'));out:write(string.format('{"passed":true,"staged":%d,"PPU_jobs":%d,"PPU_start":%d,"PPU_end":%d,"ACK_master":%d,"ACK_scanline":%d,"fault_reads":%d,"strategy":%d,"sparse_cost":%d,"column_cost":%d}',staged,jobdone,ppu_start,ppu_end,s.masterClock,s['ppu.scanline'],faultreads,emu.read(0x7a,emu.memType.snesWorkRam),emu.read(0x68,emu.memType.snesWorkRam)+256*emu.read(0x69,emu.memType.snesWorkRam),emu.read(0x6a,emu.memType.snesWorkRam)+256*emu.read(0x6b,emu.memType.snesWorkRam)));out:close();bus:close();timings:close();emu.stop(0)
 elseif a==0x606f then
  assert(STOP and v==0xee and not ppu_start and staged==1);local out=assert(io.open(OUT..'/cpu-result.json','w'));out:write('{"passed":true,"STOP":true,"final_ACK":false,"PPU_jobs":0}');out:close();bus:close();timings:close();emu.stop(0)
 end
end,emu.callbackType.write,0x604c,0x606f)
emu.addMemoryCallback(function(a,v)return note(0,a,v)end,emu.callbackType.read,0x4212)
emu.addMemoryCallback(function(a,v)return note(0,a,v)end,emu.callbackType.read,0x2137,0x213f)
emu.addMemoryCallback(function(a,v)note(1,a,v)end,emu.callbackType.write,0x2100,0x2133)
emu.addMemoryCallback(function(a,v)note(1,a,v)end,emu.callbackType.write,0x4300,0x4334)
emu.addMemoryCallback(function(a,v)note(1,a,v)end,emu.callbackType.write,0x420b,0x420c)
emu.addMemoryCallback(function()mark('stage_done')end,emu.callbackType.exec,LABELS.stage_done383)
emu.addMemoryCallback(function()local s=state();assert(s['ppu.scanline']>=225);ppu_start=ppu_start or s.masterClock;mark('PPU_trigger')end,emu.callbackType.exec,LABELS.ppu383)
emu.addMemoryCallback(function()local s=state();assert(s['ppu.scanline']>=225);ppu_end=s.masterClock;jobdone=jobdone+1;mark('PPU_done')end,emu.callbackType.exec,LABELS.ppu_done383)
'''


def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--frames',default='907,908,909,910,911,912,913,914,915,916');a=p.parse_args();root=a.out.resolve();assert root.as_posix().isascii(),'Use an ASCII private run directory for Mesen Lua';root.mkdir(parents=True,exist_ok=False);oracle,_=plans();results=[]
 for frame,stop in [(f,False) for f in map(int,a.frames.split(','))]+[(907,True)]:
  d=root/(str(frame)+('-stop' if stop else ''));d.mkdir();body,labels=rom(d);jobs=fixtures(frame);bank=(frame-905)%2
  prior=(oracle/f'expected-{frame-906}.bin').read_bytes();expected=(oracle/f'expected-{frame-904}.bin').read_bytes()
  view=current_view(frame);(d/'current-display.hex').write_text(view.hex()+'\n')
  (d/'fixture.json').write_text(json.dumps(jobs,indent=2)+'\n')
  header='local OUT='+json.dumps(d.as_posix())+'\nlocal BANK='+str(bank)+'\nlocal STOP='+str(stop).lower()+'\nlocal VIEW={'+','.join(map(str,view))+'}\n'
  header+='local LABELS={'+','.join(n+'='+str(v) for n,v in labels.items())+'}\nlocal JOBS={'+','.join('{typed='+str(j['typed']).lower()+',descriptor="'+j['descriptor']+'",data="'+j['data']+'",token='+str(j['token'])+',target='+str(j['target'])+'}' for j in jobs)+'}\n'
  for name,data in [('INITMAP',prior[:4096]),('INITOAM',prior[4608:5152]),('EXPECTMAP',expected[:4096]),('EXPECTOAM',expected[4608:5152])]:header+='local '+name+'="'+data.hex()+'"\n'
  guarded="local original_assert=assert\nfunction assert(v,msg)if not v then local e=io.open(OUT..'/error.txt','a');e:write(tostring(msg)..'\\n'..debug.traceback()..'\\n');e:close();emu.stop(1)end;return original_assert(v,msg)end\n"+LUA
  (d/'capture.lua').write_text(header+guarded,newline='\n');env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
  with (d/'mesen.log').open('wb') as log:
   r=subprocess.run(['C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe','--testRunner',str(d/'capture.lua'),str(d/'spool.sfc'),'--timeout=30','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=50,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(d/'mesen.log').read_text(errors='replace')[-2000:]
  result=json.loads((d/'cpu-result.json').read_text());assert result['passed'];result.update(frame=frame,body_bytes=body,ROM=sha(d/'spool.sfc'),events=sha(d/'events.csv'),timings=sha(d/'timings.csv'),fixture=sha(d/'fixture.json'));results.append(result);print(json.dumps(result),flush=True)
 report=dict(passed=True,cases=results,WRAM=dict(tile_spool=8192,job_records=4096,map_images=8192,column_pack=4096,column_bounds=128,cache_validity=1,total=24705),initial_bank_images_preloaded=True,fullresident=False,cold=False,physical=False,source=sha(Path(__file__)))
 (root/'result.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
if __name__=='__main__':main()
