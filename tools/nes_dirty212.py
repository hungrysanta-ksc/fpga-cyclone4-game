# SPDX-License-Identifier: MIT
"""Candidate212 sparse inactive-bank consumer. Not an installable release.

BEGIN12 = version2121, target16, last displayed serial32, immutable epoch32.
SEAL168 = previous24-byte layout/version2121 + referenced BG/OBJ bitmap144.
Patterns use checked op7; maps use aligned64-byte DATA/RLE; COPY6 is rejected.
Private WRAM bitmaps1280..144f and command storage7E4000..6607, no save SRAM.
"""
from pathlib import Path
import argparse, inspect, json
import nes_bulk195 as prior
import nes_client181 as client
import nes_native_local165 as old
import nes_banked169 as banked
from nes_clip178 import replace
call=old.call

def source181(s):
 s=prior.source181(s)
 s=replace(s,'(0x1220,0x1242)', '(0x1220,0x144e)')
 s=replace(s,"c.emit(0xc9,6,0);cond(0xf0,'inherit185')", "c.emit(0xc9,6,0);cond(0xf0,'bad_packet')")
 a=s.index(" c.label('inherit185');");b=s.index(" c.label('begin');",a);s=s[:a]+s[b:]
 a=s.index(' # A still holds the validated destination');b=s.index(" lda(0x1200);c.emit(0xc9,4);",a)
 s=s[:a]+" c.emit(0xe2,0x20);c.store(0x2183,1)\n"+s[b:]
 s=replace(s,'checkimm(0x120a,0);checkimm(0x120c,0)', 'checkimm(0x120a,0);checkimm(0x120c,12)')
 # Base is checked before replacing the current packet serial.
 s=replace(s,' # Exact monotonically increasing32-bit serial, exhausted until common reset.', ''' c.long(0xaf,0x400010);c.emit(0xc9,0x21,0x21);cond(0xd0,'bad_packet')
 for a,b in [(0x400014,0x1248),(0x400016,0x124a)]:c.long(0xaf,a);cmp(b);cond(0xd0,'bad_packet')
 lda(0x1024);c.emit(0x29,255,0);cond(0xf0,'epoch_first212')
 for a,b in [(0x400018,0x124c),(0x40001a,0x124e)]:c.long(0xaf,a);cmp(b);cond(0xd0,'bad_packet')
 c.label('epoch_first212')
 for a,b in [(0x400018,0x124c),(0x40001a,0x124e)]:c.long(0xaf,a);sta(b)
 # Exact monotonically increasing32-bit serial, exhausted until common reset.''')
 s=replace(s,"c.label('base_ready');sta(0x1020);c.jump('accepted')", '''c.label('base_ready');sta(0x1020);c.emit(0x2a,0x2a,0x29,1,0);sta(0x1034)
 c.long(0xaf,0x400012);cmp(0x1034);cond(0xd0,'bad_packet')
 lda(0x1034);cond(0xf0,'valid_a212');imm(152)
 c.label('valid_a212');sta(0x1254);c.absolute(0x9c,0x1250)
 c.emit(0xa2,150,0);c.label('dirty_clear212');c.absolute(0x9e,0x1280);c.emit(0xca,0xca);c.branch(0x10,'dirty_clear212');c.jump('accepted')''')
 s=replace(s," c.absolute(0xbd,0x1080);cmp(0x120a);cond(0xd0,'bad_packet')", " c.emit(0xe0,6,0);cond(0x90,'sparse212');c.absolute(0xbd,0x1080);cmp(0x120a);cond(0xd0,'bad_packet');c.label('sparse212')")
 s=replace(s,"c.label('data_size_ok');lda(0x1234);c.absolute(0x9d,0x1080)", "c.label('data_size_ok');lda(0x1234);c.absolute(0x9d,0x1080);c.emit(0xda);call(c,'mark212');c.emit(0xfa);cond(0x90,'bad_packet')")
 s=replace(s,'checkimm(0x120c,24)', 'checkimm(0x120c,168)')
 s=replace(s,"c.long(0xbf,0x400010);c.absolute(0xdd,0x1080);cond(0xd0,'bad_packet');c.absolute(0x9d,0x1000)", "c.long(0xbf,0x400010);c.emit(0xe0,6,0);cond(0x90,'sparse_size212');c.absolute(0xdd,0x1080);cond(0xd0,'bad_packet');c.label('sparse_size212');c.absolute(0x9d,0x1000)")
 s=replace(s,'c.emit(0xc9,0x41,0x19)', 'c.emit(0xc9,0x21,0x21)')
 s=replace(s,"call(c,'validate181');cond(0x90,'bad_packet')", "call(c,'validate181');cond(0x90,'bad_packet');call(c,'coverage212');cond(0x90,'bad_packet')")
 s=replace(s,' lda(0x1226);sta(0x1244)', ' lda(0x1222);sta(0x1248);lda(0x1224);sta(0x124a)\n lda(0x1226);sta(0x1244)')
 return s

def emit(c,prefix='local165',service=None):
 """No payload compare. Every sparse write records exact VRAM work."""
 start=len(c.data)
 def lda(a):c.absolute(0xad,a)
 def sta(a):c.absolute(0x8d,a)
 def imm(v):c.emit(0xa9);c.word(v)
 def cond(op,s):c.emit(op^0x20,3);c.jump(s)
 c.label(prefix+'_entry');c.emit(0xe2,0x20);c.store(0x1025,1);c.emit(0xc2,0x20,0x60)
 # Section0/1/2 write validation. All other sections retain sequential bounds.
 c.label('mark212');c.emit(0xe0,6,0);cond(0xb0,'mark_ok212')
 c.emit(0x8a);sta(0x60);lda(0x120a);sta(0x62);lda(0x120c);sta(0x64)
 c.emit(0xe0,4,0);cond(0xf0,'map_unit212')
 lda(0x1200);c.emit(0x29,255,0,0xc9,7,0);cond(0xd0,'mark_bad212')
 c.emit(0xe0,0,0);cond(0xd0,'obj_unit212');imm(16);sta(0x66);c.absolute(0x9c,0x68);c.jump('units212')
 c.label('obj_unit212');imm(32);sta(0x66);imm(1024);sta(0x68);c.jump('units212')
 c.label('map_unit212');lda(0x120a);c.absolute(0x0d,0x120c);c.emit(0x29,63,0);cond(0xd0,'mark_bad212');imm(64);sta(0x66);imm(1152);sta(0x68)
 c.label('units212');lda(0x62);sta(0x6a);lda(0x64);sta(0x6c);lda(0x66);sta(0x6e)
 c.label('shift212');c.absolute(0x4e,0x6a);c.absolute(0x4e,0x6c);c.absolute(0x4e,0x6e);lda(0x6e);c.emit(0xc9,1,0);c.branch(0xd0,'shift212')
 lda(0x6a);c.emit(0x18);c.absolute(0x6d,0x68);sta(0x6a)
 c.label('bits212');lda(0x6a);c.emit(0x29,7,0,0xa8);imm(1)
 c.label('bit_shift212');c.emit(0xc0,0,0);c.branch(0xf0,'bit_ready212');c.emit(0x0a,0x88);c.branch(0x80,'bit_shift212')
 c.label('bit_ready212');sta(0x6e);lda(0x6a);c.emit(0x4a,0x4a,0x4a,0xaa,0x18);c.absolute(0x6d,0x1254);c.emit(0xa8,0xe2,0x20)
 c.absolute(0xbd,0x1280);c.absolute(0x2d,0x6e);c.emit(0xc2,0x20);cond(0xd0,'mark_bad212')
 c.emit(0xe2,0x20);c.absolute(0xbd,0x1280);c.absolute(0x0d,0x6e);c.absolute(0x9d,0x1280)
 c.absolute(0xb9,0x1320);c.absolute(0x0d,0x6e);c.absolute(0x99,0x1320);c.emit(0xc2,0x20)
 c.absolute(0xee,0x6a);c.absolute(0xce,0x6c);cond(0xd0,'bits212')
 # Source and destination addresses use exactly the same bank chosen at BEGIN.
 c.absolute(0xae,0x60);pos=len(c.data);c.long(0xbf,0);srcfix=pos+1
 c.emit(0x18);c.absolute(0x6d,0x1020);c.absolute(0x6d,0x62);sta(0x70)
 lda(0x1034);c.emit(0x0a);sta(0x74);c.emit(0x0a,0x18);c.absolute(0x6d,0x74);c.absolute(0x6d,0x60);c.emit(0xaa)
 pos=len(c.data);c.long(0xbf,0);dstfix=pos+1;c.emit(0x18);c.absolute(0x6d,0x62);sta(0x72);lda(0x64);sta(0x74)
 call(c,'append212');c.emit(0x60)
 c.label('mark_bad212');c.emit(0x18,0x60)
 c.label('mark_ok212');c.emit(0x38,0x60)
 # List entries source/dest/size, stride8. At most1216 disjoint units +raw.
 # Coalescing adjacent received ranges avoids one VBlank/DMA per tile.
 c.label('append212');lda(0x1250);cond(0xf0,'append_new212');c.emit(0x38,0xe9,8,0,0xaa)
 c.long(0xbf,0x7e4004);sta(0x76);c.emit(0x18);c.absolute(0x6d,0x74);c.emit(0xc9,1,16);cond(0xb0,'append_new212');sta(0x78)
 c.long(0xbf,0x7e4000);c.emit(0x18);c.absolute(0x6d,0x76);c.absolute(0xcd,0x70);cond(0xd0,'append_new212')
 c.long(0xbf,0x7e4002);c.emit(0x18);c.absolute(0x6d,0x76);c.absolute(0xcd,0x72);cond(0xd0,'append_new212')
 lda(0x78);c.long(0x9f,0x7e4004);c.emit(0x38,0x60)
 c.label('append_new212');lda(0x1250);c.emit(0xc9,8,38);cond(0xb0,'mark_bad212');c.emit(0xaa)
 for a,b in [(0x70,0x7e4000),(0x72,0x7e4002),(0x74,0x7e4004)]:lda(a);c.long(0x9f,b)
 c.emit(0x8a,0x18,0x69,8,0);sta(0x1250);c.emit(0x38,0x60)
 # Used slots must be initialized in THIS destination, including current writes.
 c.label('coverage212');c.emit(0xa2,0,0)
 c.label('coverage_loop212');c.emit(0x8a,0x18);c.absolute(0x6d,0x1254);c.emit(0xa8)
 c.absolute(0xb9,0x1320);c.emit(0x49,255,255);sta(0x70);c.long(0xbf,0x400028);c.absolute(0x2d,0x70);cond(0xd0,'mark_bad212')
 c.emit(0xe8,0xe8,0xe0,144,0);c.branch(0xd0,'coverage_loop212')
 c.emit(0x8a,0x18);c.absolute(0x6d,0x1254);c.emit(0xaa)
 c.emit(0xa0,4,0);c.label('map_coverage212');c.absolute(0xbd,0x1320);c.emit(0xc9,255,255);cond(0xd0,'mark_bad212');c.emit(0xe8,0xe8,0x88);c.branch(0xd0,'map_coverage212')
 # Former full-frame length requirements retained where appropriate.
 for a,mask,limit in [(0x1000,15,16384),(0x1002,31,4096)]:
  lda(a);c.emit(0x89);c.word(mask);cond(0xd0,'mark_bad212');c.emit(0xc9);c.word(limit+1);cond(0xb0,'mark_bad212')
 lda(0x1000);cond(0xf0,'mark_bad212')
 for a,v in [(0x1004,4096),(0x1006,512),(0x1008,544)]:lda(a);c.emit(0xc9);c.word(v);cond(0xd0,'mark_bad212')
 c.emit(0x38,0x60)
 for values,fix in [([0,0x4000,0x5000],srcfix),([0,0x4000,0x6000,0xc000,0x8000,0xa000],dstfix)]:
  c.data[fix:fix+3]=(c.base+len(c.data)).to_bytes(3,'little')
  for v in values:c.word(v)
 return dict(code_bytes=len(c.data)-start,payload_comparison=False,command_capacity=1217)

def emit_upload(c,prefix='upload165'):
 start=len(c.data)
 def lda(a):c.absolute(0xad,a)
 def sta(a):c.absolute(0x8d,a)
 def imm(v):c.emit(0xa9);c.word(v)
 def cond(op,s):c.emit(op^0x20,3);c.jump(s)
 c.label(prefix+'_entry')
 # Raw row patches retain exact full2048B content and mode/HDMA semantics.
 lda(0x1240);cond(0xf0,'no_raw212');lda(0x1020);c.emit(0x18,0x69,0x61,0x69);sta(0x70)
 lda(0x1034);cond(0xf0,'raw_a212');imm(0x9000);c.jump('raw_dest212')
 c.label('raw_a212');imm(0x5000)
 c.label('raw_dest212');sta(0x72);imm(2048);sta(0x74);call(c,'append212');cond(0x90,'cancel169')
 c.label('no_raw212');c.absolute(0x9c,0x1252);c.absolute(0x9c,0x1256)
 c.label('upload_loop212');lda(0x1252);c.absolute(0xcd,0x1250);cond(0xb0,'final212');c.emit(0xaa)
 c.long(0xbf,0x7e4004);sta(0x103a);c.emit(0x18,0x69,96,0);sta(0x74)
 lda(0x1256);c.absolute(0xcd,0x74);cond(0xb0,'transfer212')
 call(c,'wait169');cond(0x90,'upload_return212');imm(4192);sta(0x1256)
 c.label('transfer212');lda(0x1256);c.emit(0x38);c.absolute(0xed,0x74);sta(0x1256);c.absolute(0xae,0x1252)
 c.long(0xbf,0x7e4000);sta(0x4302);c.long(0xbf,0x7e4002);c.emit(0x4a);sta(0x2116);lda(0x103a);sta(0x4305)
 c.emit(0xe2,0x20)
 for a,v in [(0x4300,1),(0x4301,0x18),(0x4304,0x7f),(0x420b,1)]:c.store(a,v)
 c.emit(0xc2,0x20);lda(0x1252);c.emit(0x18,0x69,8,0);sta(0x1252);c.jump('upload_loop212')
 c.label('final212')
 # Final palette/OAM and PPU bank selection share the current VBlank when
 # its charged budget permits; mandatory second VBlank would cap us at30Hz.
 for slot,source,size,kind in [(0,0x6000,512,1),(8,0x6200,544,2)]:
  lda(0x1020);c.emit(0x18,0x69);c.word(source);sta(0x1100+slot);imm(size);sta(0x1104+slot);imm(kind);sta(0x1106+slot)
 imm(2);sta(0x1026);c.emit(0xe2,0x20);c.store(0x1025,2);c.emit(0xc2,0x20);call(c,'final_upload212_entry')
 c.label('upload_return212');c.emit(0xc2,0x20,0x60)
 # Keep old final palette/OAM/scroll setup, serviced wait, and raw support.
 s=inspect.getsource(old.emit_upload)
 a=s.index(" c.absolute(0xad,0x1024);cond(0xf0,'blank_ready')");b=s.index(" label('blank_ready');",a)
 s=s[:a]+""" c.emit(0xc2,0x20);call(c,'service');c.absolute(0xad,0x1236);cond(0xd0,'cancel212')
 # 512 palette +544 OAM +2*96 DMA setup +320 final register/control margin.
 c.absolute(0xad,0x1256);c.emit(0xc9,0x20,6);cond(0xb0,'same_blank212')
 call(c,'wait169');cond(0x90,'return')
 label('same_blank212');c.emit(0xe2,0x20)
"""+s[b:]
 a=s.index(" c.absolute(0xad,0x1024);cond(0xd0,'scroll')");b=s.index(" label('scroll')",a);s=s[:a]+s[b:]
 s=replace(s," label('scroll')", " label('scroll');c.emit(0xc2,0x20);c.absolute(0xad,0x1034);c.absolute(0x8d,0x1032);c.emit(0xe2,0x20);call(c,'select169');call(c,'display181')")
 s=replace(s,"c.store(0x420c,2);c.store(0x2100,15)", "call(c,'hdma181');c.store(0x2100,15)")
 s=replace(s," return dict(entry=L('entry'),code_bytes=len(c.data)-start)", " label('cancel212');c.emit(0xe2,0x20);c.store(0x1025,0xe4);c.emit(0xc2,0x20,0x60)\n return dict(entry=L('entry'),code_bytes=len(c.data)-start)")
 ns=dict(old.__dict__);exec(compile(s,'final212','exec'),ns);ns['emit_upload'](c,'final_upload212')
 # Reuse exact selector and serviced bounded wait, without legacy fallback.
 s=inspect.getsource(banked.emit_upload);a=s.index("    c.label('select169')");b=s.index('    # Only E2/E3',a)
 ns=dict(lda=lda,sta=sta,imm=imm,cond=cond,c=c,call=lambda name:call(c,name))
 exec(compile('\n'.join(line[4:] for line in s[a:b].splitlines()),'wait-select212','exec'),ns)
 client.emit_extra(c)
 return dict(code_bytes=len(c.data)-start,inactive_only=True,charged_vblank_bytes=4192,full_compare=False)

def build(out):
 s=inspect.getsource(prior.build)
 s=replace(s,' class Inspect:', ''' boot_source=replace(boot_source,"call(c,'local165_entry');call(c,'large169');lda(0x1236)","call(c,'local165_entry');lda(0x1236)")
 class Inspect:''')
 s=replace(s,"'from nes_rawsteady181 import emit;from nes_client181 import call,OFFSETS,LIMITS,emit_upload'", "'from nes_dirty212 import emit,emit_upload;from nes_client181 import call,OFFSETS,LIMITS'")
 ns=dict(prior.__dict__);ns['source181']=source181
 exec(compile(s,'build212','exec'),ns);r=ns['build'](out)
 r.update(candidate='dirty212',sink_version='2121',seal_version='2121',seal_bytes=168,metadata_end=0x1450,extra_persistent_ram=522,
          private_snes_command_bytes=9736,command_address='7E4000..6607',save_sram=False,production_controller=False,scope=__doc__)
 (out/'build.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');return r

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);print(json.dumps(build(p.parse_args().out),indent=2))
