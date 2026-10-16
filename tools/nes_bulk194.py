# SPDX-License-Identifier: MIT
"""Checked direct tile DMA7; existing186 section/VRAM/final ACK retained.

op7 has physical payload4 (chunk token), expanded length16..2048. Only BG/OBJ.
The immutable descriptor at6040 matches before DMA400800 -> inactive WRAM.
Consume6050 is transport retirement only, never a display acknowledgement.
"""
from pathlib import Path
import argparse,inspect,json,shutil
import nes_copy186 as prior
import nes_rawsteady181 as steady
import nes_client181 as client
from nes_clip178 import replace

def source181(s):
 s=prior.source181(s)
 s=replace(s,"c.emit(0xc9,6,0);c.branch(0xf0,'packed_header181');", "c.emit(0xc9,6,0);c.branch(0xf0,'packed_header181');c.emit(0xc9,7,0);c.branch(0xf0,'packed_header181');")
 s=replace(s," c.emit(0xc9,6,0);cond(0xf0,'inherit185')", " c.emit(0xc9,7,0);cond(0xf0,'bulk194')\n c.emit(0xc9,6,0);cond(0xf0,'inherit185')")
 s=replace(s," c.label('inherit185');", """ c.label('bulk194');checkimm(0x120c,4)
 # Ready/kind are one word; section is restricted to BG/OBJ before using it.
 lda(0x1201);c.emit(0x29,255,0,0xc9,2,0);cond(0xb0,'bad_packet')
 c.emit(0xeb,0x09,1,0);cmp(0x6040);cond(0xd0,'bad_packet')
 lda(0x1208);cmp(0x6046);cond(0xd0,'bad_packet')
 lda(0x120a);cmp(0x6044);cond(0xd0,'bad_packet')
 for a,b in [(0x400010,0x6048),(0x400012,0x604a)]:
  c.long(0xaf,a);cmp(b);cond(0xd0,'bad_packet')
 lda(0x120e);cond(0xf0,'bad_packet');cmp(0x6042);cond(0xd0,'bad_packet')
 c.emit(0xc9,1,8);cond(0xb0,'bad_packet');sta(0x120c)
 # Both offset and length must be tile aligned (16 BG,32 OBJ).
 c.absolute(0x0d,0x120a);sta(0x70);lda(0x1201);c.emit(0x29,255,0);c.branch(0xf0,'bg_align194')
 lda(0x70);c.emit(0x29,31,0);c.jump('aligned194')
 c.label('bg_align194');lda(0x70);c.emit(0x29,15,0)
 c.label('aligned194');cond(0xd0,'bad_packet');c.jump('data')
 c.label('inherit185');""")
 # Shared DMA setup also replaces five byte stores with two word stores.
 s=replace(s," for a,v in [(0x4300,0),(0x4301,0x80),(0x4302,16),(0x4303,0),(0x4304,0x40)]:c.store(a,v)", """ c.emit(0xc2,0x20);imm(0x8000);sta(0x4300);imm(16);sta(0x4302)
 lda(0x1200);c.emit(0x29,255,0,0xc9,7,0);c.branch(0xd0,'dma_source194')
 imm(0x0800);sta(0x4302)
 c.label('dma_source194');c.emit(0xe2,0x20);c.store(0x4304,0x40)""")
 s=replace(s," c.label('accepted');imm(0);", """ c.label('accepted');lda(0x1200);c.emit(0x29,255,0,0xc9,7,0);c.branch(0xd0,'accepted194')
 # Bounded2KiB DMA has completed before the ownership token is published.
 call(c,'service');lda(0x1236);cond(0xd0,'stop_packet')
 for a,b in [(0x400010,0x604c),(0x400012,0x604e)]:c.long(0xaf,a);sta(b)
 c.emit(0xe2,0x20);c.store(0x6050,0xa5);c.emit(0xc2,0x20)
 c.label('accepted194');imm(0);""")
 s=replace(s,'c.emit(0xc9,0x61,0x18)','c.emit(0xc9,0x41,0x19)')
 # Explicit candidate8KiB ROM: body must never overlap header/vectors.
 # This is not the deployed4KiB image; board ROM/mux and resource fit are gated.
 s=replace(s,'compact=rom[:4096];compact[0xfc0:0x1000]=rom[0x7fc0:]',
             'compact=rom[:8192];compact[0x1fc0:0x2000]=rom[0x7fc0:]')
 return s

def build(out):
 out.mkdir(parents=True,exist_ok=False)
 source=inspect.getsource(client.build)
 source=replace(source,'from nes_client181 import emit,call,OFFSETS,LIMITS,emit_upload',
                'from nes_rawsteady181 import emit;from nes_client181 import call,OFFSETS,LIMITS,emit_upload')
 ns=dict(client.__dict__);ns['source181']=source181
 exec(compile(source,'bulk194-build','exec'),ns)
 steady.RelaxCode.selected=set();passes=[]
 for i in range(16):
  d=out/f'pass{i:02}';r=ns['build'](d);c=steady.RelaxCode.latest
  choice=c.next_selection();passes.append(r['body_bytes'])
  if choice==steady.RelaxCode.selected:break
  steady.RelaxCode.selected=choice
 else:raise AssertionError('relaxation did not converge')
 assert r['body_bytes']<=0x1ec0
 for p in d.iterdir():
  if p.is_file():shutil.copyfile(p,out/p.name)
 r.update(candidate='bulk194',sink_version='1941',seal_version='1941',bulk_bytes=2048,
          scope=__doc__,physical=False,production_controller=False,program_bytes=8192,
          compact4096_approved=False,relaxation_body_bytes=passes,metadata_end=0x1246,
          extra_persistent_ram=2)
 (out/'build.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');return r

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
 print(json.dumps(build(p.parse_args().out),indent=2))
