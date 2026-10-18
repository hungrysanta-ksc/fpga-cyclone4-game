# SPDX-License-Identifier: MIT
"""Actual65816 consumer for231 sparse metadata. Diagnostic until4KiB gate passes.

Unified198B bitmap:1152 pattern bits +432 metadata bits. Received at1280,
two destination-valid sets at1380, metadata end150c. Private command list
7E4000..6fff, no cartridge SRAM. Gap DMA only for fully valid destination.
"""
from pathlib import Path
import argparse,inspect,json,shutil,re
import nes_dirty212 as old
import nes_repeat227 as repeat
import nes_client181 as client
import nes_rawsteady181 as relax
from nes_delta231 import once,sha
call=old.call


class DirectCode(relax.RelaxCode):
 """Boot sets DP=DB=0; non-indexed scratch accesses have identical addresses.

 No raw-byte rewrite, indexed address shortening, or check removal. Labels
 and branch relaxation are regenerated after choosing the native DP opcode.
 """
 direct={0xad:0xa5,0x8d:0x85,0x6d:0x65,0xcd:0xc5,0xed:0xe5,0x9c:0x64,0xae:0xa6,0x8e:0x86,0xac:0xa4,0xec:0xe4,0xee:0xe6,0xce:0xc6,0x0d:0x05,0x2d:0x25,0x4e:0x46}
 def absolute(self,op,address):
  if address<256 and op in self.direct:self.emit(self.direct[op],address)
  else:super().absolute(op,address)


def source(s):
 s=repeat.source(s).replace('0x71,0x22','0x11,0x23')
 s=once(s,'from nes_rawsteady181 import RelaxCode as Code','from nes_sparse232 import DirectCode as Code')
 s=once(s,'(0x1220,0x144e)','(0x1220,0x150a)')
 s=once(s,'imm(152)','imm(198)')
 s=once(s,'c.emit(0xa2,150,0)','c.emit(0xa2,196,0)')
 s=once(s,"c.label('dirty_clear212');", "c.absolute(0x9c,0x1258);c.label('dirty_clear212');")
 s=once(s,"c.emit(0xe0,6,0);cond(0x90,'sparse212');", "c.emit(0xe0,8,0);cond(0xd0,'sparse212');")
 s=once(s,'checkimm(0x120c,168)','checkimm(0x120c,222)')
 s=once(s,"c.emit(0xe0,6,0);cond(0x90,'sparse_size212');", "c.emit(0xe0,8,0);cond(0xd0,'sparse_size212');")
 # Diagnostic ROM may exceed4KiB; no FPGA/RAM-size approval follows from it.
 s=once(s,'compact=rom[:4096];compact[0xfc0:0x1000]=rom[0x7fc0:]',
        'capacity=4096 if len(body)<=3936 else 8192;compact=rom[:capacity];compact[capacity-64:capacity]=rom[0x7fc0:]')
 return s


def emit(c,prefix='local165',service=None):
 s=inspect.getsource(old.emit)
 s=once(s,"c.label('mark212');c.emit(0xe0,6,0);cond(0xb0,'mark_ok212')", "c.label('mark212')")
 s=once(s," c.emit(0xe0,4,0);cond(0xf0,'map_unit212')", " c.emit(0xe0,4,0);cond(0xb0,'metadata232')")
 a=s.index(" c.label('map_unit212');");b=s.index(" c.label('units212');",a)
 s=s[:a]+''' c.label('metadata232');c.emit(0xe0,8,0);cond(0xf0,'mark_ok212')
 c.emit(0xe0,10,0);cond(0xd0,'aligned232')
 lda(0x62);c.emit(0xc9,0x61,4);cond(0xb0,'raw232')
 c.absolute(0xcd,0x1258);cond(0xd0,'mark_bad212');c.emit(0x18);c.absolute(0x6d,0x64)
 c.emit(0xc9,0x62,4);cond(0xb0,'mark_bad212');sta(0x1258);c.jump('mark_ok212')
 c.label('raw232');c.emit(0x38,0xe9,0x61,4);sta(0x62)
 c.label('aligned232');lda(0x62);c.emit(0x29,15,0);cond(0xd0,'mark_bad212')
 lda(0x64);c.emit(0x29,15,0);cond(0xf0,'aligned_end232')
 c.emit(0xe0,10,0);cond(0xd0,'mark_bad212');lda(0x62);c.emit(0x18);c.absolute(0x6d,0x64);c.emit(0xc9,0xf9,8);cond(0xd0,'mark_bad212')
 c.label('aligned_end232');imm(16);sta(0x66);imm(1152);c.emit(0xe0,4,0);cond(0xf0,'meta_base232')
 imm(1408);c.emit(0xe0,6,0);cond(0xf0,'meta_base232');imm(1440)
 c.label('meta_base232');sta(0x68)
''' +s[b:]
 s=once(s,'lda(0x64);sta(0x6c);','lda(0x64);c.emit(0x18,0x69,15,0);sta(0x6c);')
 s=s.replace('0x1320','0x1380')
 s=once(s,' c.absolute(0xae,0x60);pos=', ''' c.absolute(0xae,0x60);c.emit(0xe0,6,0);cond(0xf0,'mark_ok212');c.emit(0xe0,10,0);cond(0xf0,'raw_address232')
 pos=''')
 at=s.index(" c.label('mark_bad212');")
 s=s[:at]+''' c.label('raw_address232');lda(0x62);c.emit(0xc9,0,8);cond(0xb0,'mark_ok212')
 lda(0x1020);c.emit(0x18,0x69,0x61,0x69);c.absolute(0x6d,0x62);sta(0x70)
 lda(0x1034);c.emit(0x0a,0x0a,0x0a,0x0a,0xeb,0x0a,0x0a,0x18,0x69,0,0x50);c.absolute(0x6d,0x62);sta(0x72)
 imm(2048);c.emit(0x38);c.absolute(0xed,0x62);c.absolute(0xcd,0x64);cond(0x90,'raw_clip232');lda(0x64)
 c.label('raw_clip232');sta(0x74);call(c,'append212');c.emit(0x60)
''' +s[at:]
 # Store section in spare command word; never merge across section boundaries.
 a=s.index(" c.label('append212');");b=s.index(" c.label('append_new212');",a)
 s=s[:a]+''' c.label('append212');lda(0x1250);cond(0xf0,'append_new212');c.emit(0x38,0xe9,8,0,0xaa)
 c.long(0xbf,0x7e4006);c.absolute(0xcd,0x60);cond(0xd0,'append_new212')
 c.long(0xbf,0x7e4004);sta(0x76);c.long(0xbf,0x7e4000);c.emit(0x18);c.absolute(0x6d,0x76);sta(0x78)
 lda(0x70);c.emit(0x38);c.absolute(0xed,0x78);cond(0x90,'append_new212');sta(0x7c)
 cond(0xf0,'merge232')
 # These are only command descriptions. coverage212 proves ALL target
 # metadata valid before any list DMA, including every merged gap byte.
 lda(0x60);c.emit(0xc9,4,0);cond(0x90,'append_new212');lda(0x7c);c.emit(0xc9,97,0);cond(0xb0,'append_new212')
 c.label('merge232');c.long(0xbf,0x7e4002);c.emit(0x18);c.absolute(0x6d,0x76);c.absolute(0x6d,0x7c);c.absolute(0xcd,0x72);cond(0xd0,'append_new212')
 lda(0x76);c.emit(0x18);c.absolute(0x6d,0x7c);c.absolute(0x6d,0x74);c.emit(0xc9,1,16);cond(0xb0,'append_new212')
 c.long(0x9f,0x7e4004);c.emit(0x38,0x60)
''' +s[b:]
 s=once(s,'c.emit(0xc9,8,38)','c.emit(0xc9,0,48)')
 s=once(s,'(0x74,0x7e4004)]','(0x74,0x7e4004),(0x60,0x7e4006)]')
 # Every used metadata unit must be valid at SEAL before list DMA. This
 # includes gaps assembled from previous target bytes and current writes.
 a=s.index(" c.emit(0x8a,0x18);c.absolute(0x6d,0x1254);c.emit(0xaa)",s.index(" c.label('coverage_loop212')"))
 b=s.index(' # Former full-frame',a)
 s=s[:a]+''' c.absolute(0x9c,0x7c);lda(0x1240);cond(0xd0,'raw_required232')
 # A normal frame invalidates both raw bases, matching the C union lifetime.
 c.emit(0xa2,16,0);c.label('raw_invalidate232');c.absolute(0x9e,0x1434);c.absolute(0x9e,0x14fa);c.emit(0xca,0xca);c.branch(0x10,'raw_invalidate232');c.jump('coverage_count232')
 c.label('raw_required232');imm(18);sta(0x7c)
 c.label('coverage_count232');lda(0x7c);c.emit(0x18,0x69,36,0);sta(0x7c);c.emit(0xa2,0,0)
 c.label('metadata_coverage232');c.long(0xbf,0x4000b8);c.absolute(0xdd,0x1310);cond(0xd0,'mark_bad212')
 c.emit(0x8a,0x18);c.absolute(0x6d,0x1254);c.emit(0xa8);c.absolute(0xb9,0x1410);c.emit(0xc9,255,255);cond(0xd0,'mark_bad212')
 c.emit(0xe8,0xe8);c.absolute(0xec,0x7c);c.branch(0xd0,'metadata_coverage232')
 lda(0x1240);cond(0xf0,'prefix_normal232');imm(1121);c.jump('prefix_check232')
 c.label('prefix_normal232');lda(0x100a)
 c.label('prefix_check232');c.absolute(0xcd,0x1258);cond(0xd0,'mark_bad212')
''' +s[b:]
 # DP is zero by the existing client ABI. Use native direct-page encoding
 # for local scratch, preserving operation/flags and every validation branch.
 s=once(s,'def lda(a):c.absolute(0xad,a)','def lda(a):c.emit(0xa5,a) if a<256 else c.absolute(0xad,a)')
 s=once(s,'def sta(a):c.absolute(0x8d,a)','def sta(a):c.emit(0x85,a) if a<256 else c.absolute(0x8d,a)')
 dp={0xad:0xa5,0x8d:0x85,0x6d:0x65,0xcd:0xc5,0xed:0xe5,0x9c:0x64,0xae:0xa6,0x8e:0x86,0xac:0xa4,0xec:0xe4,0xee:0xe6,0xce:0xc6,0x0d:0x05,0x2d:0x25,0x4e:0x46}
 def direct(m):
  op,at=(int(x,16) for x in m.groups())
  return f'c.emit({dp[op]:#x},{at:#x})' if op in dp and at<256 else m[0]
 s=re.sub(r'c\.absolute\((0x[0-9a-f]+),(0x[0-9a-f]+)\)',direct,s)
 ns=dict(old.__dict__);exec(compile(s,'sparse232-emit','exec'),ns);return ns['emit'](c,prefix,service)


def emit_upload(c,prefix='upload165'):
 s=inspect.getsource(old.emit_upload)
 a=s.index(' # Raw row patches');b=s.index(" c.label('no_raw212');",a)
 s=s[:a]+s[b:]
 s=once(s," c.label('final212')", """ c.label('final212')
 # Zero received CGRAM bits plus coverage implies target==last displayed
 # palette: host marks BOTH banks on change. Cold omission fails coverage.
 lda(0x1330);c.absolute(0x0d,0x1332);cond(0xd0,'palette_full232')
 imm(960);c.emit(0xa2,8,0);c.jump('palette_ready232')
 c.label('palette_full232');imm(1568);c.emit(0xa2,0,0)
 c.label('palette_ready232');sta(0x125c);c.absolute(0x8e,0x125e)""")
 s=once(s,';imm(kind);sta(0x1106+slot)','')
 s=once(s,'s=inspect.getsource(old.emit_upload)','s=specialize_final(inspect.getsource(old.emit_upload))')
 s=once(s,'c.emit(0xc9,0x20,6)','c.absolute(0xcd,0x125c)')
 ns=dict(old.__dict__);ns['specialize_final']=specialize_final
 exec(compile(s,'sparse232-upload','exec'),ns);return ns['emit_upload'](c,prefix)


def specialize_final(s):
 # Only internally constructed fixed slots0=CGRAM/8=OAM reach this routine.
 # VRAM has its separate validated list. No packet can supply these kinds.
 a=s.index(" c.absolute(0xbd,0x1106);");b=s.index(" label('cgram');",a)
 s=s[:a]+" c.emit(0xe0,0,0);cond(0xd0,'oam')\n"+s[b:]
 s=once(s,'c.absolute(0xad,0x1026);c.emit(0x0a,0x0a,0x0a);c.absolute(0x8d,0x1070);c.emit(0xa2,0,0)',
        'c.emit(0xa9,16,0);c.absolute(0x8d,0x1070);c.absolute(0xae,0x125e)')
 return s


def build(out):
 out.mkdir(parents=True,exist_ok=False)
 boot_source=inspect.getsource(client.boot.build)
 boot_source=once(boot_source,'boot.long(0xdf,0x008100)','boot.long(0xdf,0x008060)')
 boot_source=once(boot_source,'assert len(boot.finish())<=256','assert len(boot.finish())<=96')
 boot_source=once(boot_source,"call(c,'local165_entry');call(c,'large169');lda(0x1236)","call(c,'local165_entry');lda(0x1236)")
 class Inspect:
  @staticmethod
  def getsource(fn):
   assert fn is client.boot.build
   return boot_source
 s=inspect.getsource(client.build)
 s=once(s,'from nes_client181 import emit,call,OFFSETS,LIMITS,emit_upload','from nes_sparse232 import emit,emit_upload;from nes_client181 import call,OFFSETS,LIMITS')
 ns=dict(client.__dict__);ns.update(source181=source,inspect=Inspect);exec(compile(s,'sparse232-build','exec'),ns)
 CodeType=__import__('nes_sparse232').DirectCode
 CodeType.selected=set();passes=[]
 for i in range(16):
  d=out/f'pass{i:02}';r=ns['build'](d);c=CodeType.latest;choice=c.next_selection();passes.append(r['body_bytes'])
  if choice==CodeType.selected:break
  CodeType.selected=choice
 else:raise AssertionError('relaxation did not converge')
 for p in d.iterdir():
  if p.is_file():shutil.copyfile(p,out/p.name)
 compact=bytes(int(x,16) for x in (out/'sink-program.hex').read_text().split())
 body=(out/'body.bin').read_bytes();rom=(out/'sink165.sfc').read_bytes()
 assert len(body)==r['body_bytes']==r['copy_verified_bytes']
 assert compact[96:96+len(body)]==body==rom[96:96+len(body)]
 assert compact[:96]==rom[:96] and compact[-64:]==rom[0x7fc0:]
 assert len(compact)==(4096 if len(body)<=3936 else 8192)
 assert 96+len(body)<=len(compact)-64
 r['local']['command_capacity']=1536
 r.update(candidate='sparse232',sink_version='2311',seal_bytes=222,program_bytes=len(compact),body_capacity=3936,body_free=3936-r['body_bytes'],compact4096_approved=r['body_bytes']<=3936,
          relaxation_body_bytes=passes,metadata_end=0x150c,command_capacity=1536,command_address='7E4000..6fff',save_sram=False,
          physical=False,production_bound=False,scope=__doc__,script_sha256=sha(Path(__file__)))
 (out/'build.json').write_text(json.dumps(r,indent=2)+'\n');return r


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);print(json.dumps(build(p.parse_args().out),indent=2))
