# SPDX-License-Identifier: MIT
"""Real65816 compact-plan receiver, independent map coverage and PPU DMA.

Plan generation is absent from this CPU. Warm prior images remain explicit
fixtures; this fragment is not installed fullresident firmware.
"""
import argparse,csv,inspect,json,os,struct,subprocess
from collections import OrderedDict
from pathlib import Path
import probe_nes_increment388 as old
from nes_delta231 import ROOT,BASE,sha,once

PLANS=BASE/'probes/nes-plan390/arm01'

def make_rom():
 s=inspect.getsource(old.rom)
 s=once(s," c.label('next383');", " word(0x94,0);word(0x96,0);word(0x98,0);word(0x9a,0);word(0x9c,0);word(0x9e,0)\n c.label('next383');")
 a=s.index(" lda(0x40);cond(0xd0,'abort383');")
 z=s.index(" c.label('copy383');",a)
 s=s[:a]+''' lda(0x41);c.emit(0xc9,3);c.branch(0xf0,'cg383');c.emit(0xc9,4);c.branch(0xf0,'oam391');c.emit(0xc9,5);c.branch(0xf0,'ordinary_copy383');c.emit(0xc9,6);cond(0xd0,'abort383');lda(0x94);cond(0xd0,'abort383');c.jump('ordinary_copy383')
 c.label('cg383');c.store(0x11,1);c.jump('ordinary_copy383')
 c.label('oam391');c.store(0x12,1)
 c.label('ordinary_copy383');lda(0x48);sta(0x2d);c.emit(0xc2,0x20);lda(0x42);sta(0x20);lda(0x44);sta(0x26);cond(0xf0,'abort16_383');c.emit(0xe2,0x20);c.store(0x2b,0x7f);c.store(0x2c,1)
 '''.rstrip()+'\n'+s[z:]
 a=s.index(' # Store only4B map coordinates.');z=s.index(" c.label('stage_done383');",a)
 s=s[:a]+''' # Independently reconcile the actual received map with the compact plan.
 c.label('track_map388');fault();lda(0x94);cond(0xf0,'abort383');lda(0x2d);c.absolute(0xcd,0x9e);cond(0xd0,'abort383')
 c.emit(0xc2,0x20);c.emit(0xa0,6,0,0xb7,0xa0);c.absolute(0xcd,0x35);cond(0xd0,'abort16_383')
 lda(0x26);c.emit(0x29,1,0);cond(0xd0,'abort16_383');lda(0x26);c.emit(0x4a);sta(0x72);lda(0x33);sta(0x70);c.emit(0x18);c.absolute(0x6d,0x72);cond(0xb0,'abort16_383');c.emit(0xc9,1,8);cond(0xb0,'abort16_383')
 c.absolute(0xee,0x96);lda(0x98);c.emit(0x18);c.absolute(0x6d,0x72);cond(0xb0,'abort16_383');sta(0x98);lda(0x7a);c.emit(0xc9,2,0);cond(0xf0,'coverage_done16_391');c.emit(0xc9,1,0);cond(0xf0,'coverage_column391')
 lda(0x96);c.emit(0xc9,8,0);cond(0xb0,'abort16_383');c.emit(0x3a,0x0a,0x0a,0x18,0x69,16,0,0xa8,0xb7,0xa0);c.absolute(0xcd,0x70);cond(0xd0,'abort16_383');c.emit(0xc8,0xc8,0xb7,0xa0);c.absolute(0xcd,0x72);cond(0xd0,'abort16_383');c.jump('coverage_done16_391')
 c.label('coverage_column391');c.emit(0xe2,0x20);fault();c.emit(0xc2,0x20);lda(0x70);c.emit(0x29,31,0,0x0a);sta(0x74);lda(0x70);c.emit(0x29,0,4,0x4a,0x4a,0x4a,0x4a);c.absolute(0x0d,0x74);c.emit(0x18,0x69,16,0,0xa8);lda(0x70);c.emit(0x4a,0x4a,0x4a,0x4a,0x4a,0x29,31,0);sta(0x75);c.emit(0xb7,0xa0,0x29,255,0);c.absolute(0xcd,0x75);cond(0xf0,'coverage_lo391');cond(0xb0,'abort16_383')
 c.label('coverage_lo391');c.emit(0xc8,0xb7,0xa0,0x29,255,0);c.absolute(0xcd,0x75);cond(0x90,'abort16_383');c.absolute(0xee,0x70);c.absolute(0xce,0x72);cond(0xd0,'coverage_column391')
 c.label('coverage_done16_391');c.emit(0xe2,0x20);c.jump('stage_done383')
 c.label('metadata391');fault();lda(0x40);cond(0xd0,'abort383');word(0xa0,0x7500);c.store(0xa2,0x7f);lda(0x2d);sta(0x9e);c.branch(0xf0,'meta_base391');word(0xa0,0xf500)
 c.label('meta_base391');c.emit(0xc2,0x20);lda(0x20);c.absolute(0xcd,0xa0);cond(0xd0,'abort16_383');c.emit(0xa0,0,0,0xb7,0xa0,0xc9,0x4d,0x50);cond(0xd0,'abort16_383');c.emit(0xa0,2,0,0xb7,0xa0,0x29,255,0,0xc9,1,0);cond(0xd0,'abort16_383');c.emit(0xa0,3,0,0xb7,0xa0,0x29,255,0,0xc9,3,0);cond(0xb0,'abort16_383');sta(0x7a)
 c.emit(0xa0,4,0,0xb7,0xa0);c.absolute(0xcd,0x9e);cond(0xd0,'abort16_383');c.emit(0xa0,12,0,0xb7,0xa0);sta(0x9a);c.emit(0xa0,14,0,0xb7,0xa0);sta(0x9c);c.emit(0xc9,1,8);cond(0xb0,'abort16_383')
 lda(0x7a);c.emit(0xc9,1,0);c.branch(0xf0,'meta_column391');c.emit(0xc9,2,0);c.branch(0xf0,'meta_dense391');lda(0x9a);c.emit(0xc9,8,0);cond(0xb0,'abort16_383');c.emit(0x0a,0x0a,0x18,0x69,16,0);c.jump('meta_len391')
 c.label('meta_dense391');c.emit(0xa9,16,0);c.jump('meta_len391');c.label('meta_column391');c.emit(0xa9,144,0)
 c.label('meta_len391');c.absolute(0xcd,0x26);cond(0xd0,'abort16_383');word(0x94,1);c.emit(0xe2,0x20);c.jump('stage_done_token391')
 '''.rstrip()+'\n'+s[z:]
 s=once(s," c.label('stage_done383');fault()",''' c.label('stage_done383');fault();lda(0x2c);c.emit(0xc9,1);cond(0xd0,'stage_done_token391');lda(0x41);c.emit(0xc9,6);cond(0xf0,'metadata391');lda(0x40);cond(0xf0,'stage_done_token391')
 # The only fixed zero expansion is the existing authenticated HDMA tail.
 lda(0x41);c.emit(0xc9,5);cond(0xd0,'abort383');c.emit(0xc2,0x20);lda(0x26);c.emit(0xc9,2,0);cond(0xd0,'abort16_383');lda(0x20);c.emit(0x29,255,0x7f,0xc9,21,0x65);cond(0xd0,'abort16_383');lda(0x20);sta(0x2181);word(0x4305,1100);c.emit(0xe2,0x20)
 for a,v in ((0x4300,8),(0x4301,0x80),(0x4304,0)):c.store(a,v)
 c.emit(0xc2,0x20);c.emit(0xa9,0,0);zero_patch391=len(c.data)-2;sta(0x4302);c.emit(0xe2,0x20);c.store(0x420b,1)
 c.label('stage_done_token391');fault()''')
 a=s.index(' # No map reparse/compaction');z=s.index(" c.label('map_job_done383')",a)
 # Keep the existing sparse and column DMA builders, replacing their inputs
 # by ARM coordinates. No native dirty list, bounds construction or cost scan.
 oldpart=s[a:z];sp=oldpart.index(" c.label('sparse388');");co=oldpart.index(" c.label('columns386');")
 sparse=oldpart[sp:co]
 sparse=sparse.replace("word(0x66,0xac00)","word(0x66,0)")
 sparse=sparse.replace("c.absolute(0xae,0x66);c.absolute(0xec,0x8e)","lda(0x66);c.absolute(0xcd,0x9a)")
 sparse=sparse.replace(" far(0xbf,0x7e0000);c.emit(0x18);", " lda(0x66);c.emit(0x0a,0x0a,0x18,0x69,16,0,0xa8,0xb7,0xa0);sta(0x70);c.emit(0x18);")
 sparse=sparse.replace("far(0xbf,0x7e0000);c.emit(0x0a,0x18);", "lda(0x70);c.emit(0x0a,0x18);")
 sparse=sparse.replace("far(0xbf,0x7e0002);sta(0x26);", "c.emit(0xc8,0xc8,0xb7,0xa0,0x0a);sta(0x26);")
 sparse=sparse.replace("c.emit(0x18,0x69,4,0)","c.emit(0x1a)")
 columns=oldpart[co:]
 start=columns.index(" c.label('column_loop386');");end=columns.index(" lda(0x70);c.emit(0x0a,0x0a",start)
 columns=columns[:start]+''' c.label('column_loop386');fault();c.emit(0xc2,0x20);lda(0x66);c.emit(0x0a);sta(0x76);c.emit(0x18,0x69,16,0,0xa8,0xb7,0xa0,0x29,255,0);sta(0x70);c.emit(0xc9,32,0);cond(0xf0,'column_next391');cond(0xb0,'abort16_383');c.emit(0xc8,0xb7,0xa0,0x29,255,0,0xc9,32,0);cond(0xb0,'abort16_383');c.emit(0x38);c.absolute(0xed,0x70);cond(0x90,'abort16_383');c.emit(0x1a);sta(0x72);c.emit(0x0a);sta(0x26)
 '''.rstrip()+'\n'+columns[end:]
 columns=columns.replace("c.emit(0xc2,0x20);c.absolute(0xee,0x66);lda(0x66);c.absolute(0xcd,0x8c)","c.label('column_next391');c.emit(0xc2,0x20);c.absolute(0xee,0x66);lda(0x66);c.emit(0xc9,64,0)")
 s=s[:a]+''' lda(0x94);cond(0xf0,'abort383');lda(0x1000);c.absolute(0xcd,0x9e);cond(0xd0,'abort383')
 lda(0x1000);c.branch(0xf0,'valid_bank0_386');far(0xaf,0x7ef080);c.emit(0x29,2);c.branch(0x80,'valid_test386');c.label('valid_bank0_386');far(0xaf,0x7ef080);c.emit(0x29,1);c.label('valid_test386');cond(0xf0,'abort383')
 c.emit(0xc2,0x20);lda(0x96);c.absolute(0xcd,0x9a);cond(0xd0,'abort16_383');lda(0x98);c.absolute(0xcd,0x9c);cond(0xd0,'abort16_383');c.emit(0xe2,0x20);word(0x78,0xc000);word(0x7c,0x3000);lda(0x1000);c.branch(0xf0,'bases388');word(0x78,0xd000);word(0x7c,0x5000)
 c.label('bases388');lda(0x7a);cond(0xf0,'sparse388');c.emit(0xc9,1);cond(0xf0,'columns386');word(0x20,0xc000);lda(0x1000);c.branch(0xf0,'dense_base391');word(0x20,0xd000);c.label('dense_base391');word(0x26,4096);c.emit(0xc2,0x20);lda(0x7c);sta(0x28);c.emit(0xe2,0x20);c.store(0x2a,0);c.store(0x2b,0x7e);job();c.jump('map_job_done383')
 '''.rstrip()+'\n'+sparse+columns+s[z:]
 s=once(s,"c.labels['display383']=0;prefix=c.finish();offset=len(prefix)","c.label('zero391');c.emit(0);c.data[zero_patch391:zero_patch391+2]=struct.pack('<H',c.labels['zero391']);c.labels['display383']=0;prefix=c.finish();offset=len(prefix)")
 s=s.replace("b'NES388 INCREMENTAL   '","b'NES391 COMPACT PLAN  '")
 ns=dict(old.__dict__);exec(compile(s,'native391-generated','exec'),ns);return ns['rom']

rom=make_rom()

def fixtures(f):
 jobs=old.fixtures(f);bytoken={j['token']:j for j in jobs};result=[];groups=OrderedDict()
 for x in csv.reader((BASE/'probes/nes-present378/control02/joint-events.csv').read_text().splitlines()):
  if x[:2]==['read336',str(f)]:groups.setdefault(int(x[2]),[]).append(x)
 bank=(f-905)%2;inserted=False
 for token,rows in groups.items():
  op,section,pos=map(int,rows[0][3:6]);data=bytes(int(x[7])for x in rows)
  if op in (12,14)and not inserted:
   b=(PLANS/f'plan{f}.bin').read_bytes();desc=bytes([0,6])+struct.pack('<HHH',0x7500+bank*0x8000,len(b),0)+bytes([bank]);result.append(dict(typed=False,descriptor=desc.hex(),data=b.hex(),token=0x7f000001,kind=6,target=0,bank=bank));inserted=True
  if token in bytoken:result.append(bytoken[token])
  elif section==5:
   target=0x6500+bank*0x8000+pos;zero=op==5 and pos==21 and data==b'\0\0';desc=bytes([int(zero),5])+struct.pack('<HHH',target,len(data),pos//2)+bytes([bank]);result.append(dict(typed=False,descriptor=desc.hex(),data=data.hex(),token=token,kind=5,target=pos//2,bank=bank))
 assert inserted;return result

LUA=old.LUA.replace("for _,a in ipairs({0x16500", "for i,b in ipairs(bytes(INITHDMA))do emu.write(0x16500+BANK*0x8000+i-1,b,emu.memType.snesWorkRam)end\nfor _,a in ipairs({0x16500")
LUA=LUA.replace("for _,a in ipairs({0x16500,0x17161,0x17203,0x1e500,0x1f1b2,0x1f203})do emu.write(a,0,emu.memType.snesWorkRam)end", "")
LUA=LUA.replace("  local out=assert(io.open(OUT..'/cpu-result.json','w'));", "  for i,b in ipairs(bytes(EXPECTHDMA))do assert(emu.read(0x16500+BANK*0x8000+i-1,emu.memType.snesWorkRam)==b,'HDMA WRAM '..i..':'..emu.read(0x16500+BANK*0x8000+i-1,emu.memType.snesWorkRam)..'/'..b)end\n  local out=assert(io.open(OUT..'/cpu-result.json','w'));")

def main():
 # Reuse the exact emulator driver, replacing only the candidate generator,
 # fixtures and the additional independent whole HDMA image assertion.
 s=inspect.getsource(old.main).replace("('EXPECTOAM',expected[4608:5152])", "('EXPECTOAM',expected[4608:5152]),('INITHDMA',prior[5152:8570]),('EXPECTHDMA',expected[5152:8570])")
 s=s.replace('map_records=1024,','plan_payload=144,').replace('column_bounds=128,','').replace('dirty_columns=64,total=24769','total=23697')
 ns=dict(old.__dict__,rom=rom,fixtures=fixtures,LUA=LUA,__file__=__file__);exec(compile(s,'driver391','exec'),ns);ns['main']()
if __name__=='__main__':main()
