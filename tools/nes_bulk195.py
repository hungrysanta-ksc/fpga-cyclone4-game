# SPDX-License-Identifier: MIT
"""Fit checked194 direct DMA in the existing4KiB ROM without removing checks."""
from pathlib import Path
import argparse,inspect,json,shutil
import nes_bulk194 as prior
import nes_rawsteady181 as steady
import nes_client181 as client
from nes_clip178 import replace
ROOT=Path(__file__).resolve().parents[1]

def source181(s):
 s=prior.source181(s)
 s=replace(s,'compact=rom[:8192];compact[0x1fc0:0x2000]=rom[0x7fc0:]',
             'compact=rom[:4096];compact[0xfc0:0x1000]=rom[0x7fc0:]')
 # Boot is89B including byte-for-byte WRAM copy verification. Reserve96B.
 s=replace(s,'rom[0x100:0x100+len(body)]=body','rom[0x60:0x60+len(body)]=body')
 s=replace(s,'boot.word(0x8100)','boot.word(0x8060)')
 s=replace(s,"for a,b in [(0x1202,0x1220),(0x1204,0x1222),(0x1206,0x1224),(0x1208,0x1226)]:lda(a);cmp(b);cond(0xd0,'bad_packet')",
 "c.emit(0xa2,6,0);c.label('tokens195');c.absolute(0xbd,0x1202);c.absolute(0xdd,0x1220);cond(0xd0,'bad_packet');c.emit(0xca,0xca);c.branch(0x10,'tokens195')")
 s=replace(s,'for i in range(0,8,2):lda(0x1202+i);sta(0x6012+i)',
 "c.emit(0xa2,6,0);c.label('reply195');c.absolute(0xbd,0x1202);c.absolute(0x9d,0x6012);c.emit(0xca,0xca);c.branch(0x10,'reply195')")
 s=replace(s,'for a,b in [(0x1204,0x1222),(0x1206,0x1224),(0x1208,0x1226)]:lda(a);sta(b)',
 "c.emit(0xa2,4,0);c.label('begin195');c.absolute(0xbd,0x1204);c.absolute(0x9d,0x1222);c.emit(0xca,0xca);c.branch(0x10,'begin195')")
 # A/flags are dead after this initialization list (the next loop uses STZ).
 line=next(x for x in s.splitlines() if 'for a,v in [(0x2100,128),(0x4200,1)' in x)
 s=replace(s,line,line.replace(':c.store(a,v)',':\n  if v==0:c.absolute(0x9c,a)\n  else:c.store(a,v)'))
 # Outside VBlank this clear is followed by PLP/RTS; A/flags are not consumed.
 s=replace(s,'c.store(0x1238,0)', 'c.absolute(0x9c,0x1238)')
 return s

def build(out):
 out.mkdir(parents=True,exist_ok=False)
 # The172 verifier is inserted after source181. Relocate its ROM operand too.
 boot_source=inspect.getsource(client.boot.build)
 boot_source=replace(boot_source,'boot.long(0xdf,0x008100)','boot.long(0xdf,0x008060)')
 boot_source=replace(boot_source,'assert len(boot.finish())<=256','assert len(boot.finish())<=96')
 class Inspect:
  @staticmethod
  def getsource(fn):
   assert fn is client.boot.build
   return boot_source
 source=inspect.getsource(client.build)
 source=replace(source,'from nes_client181 import emit,call,OFFSETS,LIMITS,emit_upload',
                'from nes_rawsteady181 import emit;from nes_client181 import call,OFFSETS,LIMITS,emit_upload')
 ns=dict(client.__dict__);ns.update(source181=source181,inspect=Inspect)
 exec(compile(source,'bulk195-build','exec'),ns)
 steady.RelaxCode.selected=set();passes=[]
 for i in range(16):
  d=out/f'pass{i:02}';r=ns['build'](d);c=steady.RelaxCode.latest
  choice=c.next_selection();passes.append(r['body_bytes'])
  if choice==steady.RelaxCode.selected:break
  steady.RelaxCode.selected=choice
 else:raise AssertionError('relaxation did not converge')
 assert r['body_bytes']<=0xf60,(r['body_bytes'],0xf60)
 for p in d.iterdir():
  if p.is_file():shutil.copyfile(p,out/p.name)
 rom=(out/'sink165.sfc').read_bytes();body=(out/'body.bin').read_bytes()
 assert rom[0x60:0x60+len(body)]==body
 assert all(x==255 for x in rom[0x60+len(body):0xfc0])
 compact=bytes(int(x,16) for x in (out/'sink-program.hex').read_text().split())
 assert len(compact)==4096 and compact[:0xfc0]==rom[:0xfc0] and compact[0xfc0:]==rom[0x7fc0:]
 r.update(candidate='bulk195',sink_version='1941',seal_version='1941',bulk_bytes=2048,
          physical=False,production_controller=False,program_bytes=4096,boot_reserved_bytes=96,
          body_capacity=3936,body_free=3936-len(body),compact4096_approved=True,
          relaxation_body_bytes=passes,metadata_end=0x1246,extra_persistent_ram=2,scope=__doc__)
 (out/'build.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');return r

def prepare(old,out):
 """Paired production186 C sink, with a new checked descriptor entry point."""
 import hashlib
 out.mkdir(parents=True,exist_ok=False);pins={}
 for f in sorted(old.glob('nes_*')):
  if f.is_file() and f.suffix in ('.c','.h'):
   shutil.copyfile(f,out/f.name);pins[f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
 for name in ('nes_sink_bulk195.h','nes_sink_bulk195.inc'):
  shutil.copyfile(ROOT/'src/nes/firmware'/name,out/name)
 f=out/'nes_native_sink165.c';s=f.read_text()
 s=replace(s,'if(op!=5&&op!=6&&expanded)',
 '''if(op==7&&(!data||n!=4||section>1||!expanded||expanded>2048||
    expanded%(section?32u:16u)||at%(section?32u:16u)))return fail(s,1);
 if(op!=5&&op!=6&&op!=7&&expanded)''')
 s=replace(s,'put16(descriptor+20,0x1861)','put16(descriptor+20,0x1941)')
 s+='\n#include "nes_sink_bulk195.h"\n#include "nes_sink_bulk195.inc"\n'
 f.write_text(s,encoding='utf8',newline='\n')
 # Op7 is a synchronous barrier: drain prior metadata, publish one command,
 # then require its real SNES ACK before allowing descriptor retirement.
 f=out/'nes_sink_window184.c';s=f.read_text()
 s=replace(s,'if(p[0]!=1&&p[0]!=3)return fail(s,1);',
             'if(p[0]!=1&&p[0]!=3&&p[0]!=7)return fail(s,1);')
 f.write_text(s,encoding='utf8',newline='\n')
 r=build(out/'client')
 (out/'preparation.json').write_text(json.dumps(dict(input_pins=pins,client=r),indent=2)+'\n',encoding='utf8')
 return r

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--prior',type=Path)
 a=p.parse_args();print(json.dumps(prepare(a.prior,a.out) if a.prior else build(a.out),indent=2))
