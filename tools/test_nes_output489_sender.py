# SPDX-License-Identifier: MIT
"""Linked M4 sender ABI boundary vectors0..7, not synthetic gameplay semantics."""
import argparse,json,random,re,struct
from pathlib import Path
from audit_nes_output489 import CompactAudit,encode,sha
p=argparse.ArgumentParser(description=__doc__)
for n in ['arm','dataset','out']:p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
palette=struct.pack('<64H',*map(int,re.search(r'\{(.*?)\}',(a.arm/'nes_palette165.inc').read_text(),re.S)[1].split(',')))
class BoundaryAudit(CompactAudit):
 def call(self,name,args):
  if name=='nes_resident211_commit'and not hasattr(self,'resident_before'):
   self.resident_before=bytes(self.u.mem_read(self.resident,self.layout['nes_resident211']['size']))
  return super().call(name,args)
m=BoundaryAudit(a.arm,palette,a.out);g=(a.dataset/'frame905.geometry').read_bytes();r=(a.dataset/'frame905.raw').read_bytes();m.frame(encode(g,r,905)[0],g,r,905,1)
v=m.layout['nes_native_video165'];snapshot=(a.out/'frame905/video-before.bin').read_bytes()
for count in range(8):
 m.out=a.out/f"count{count}";m.out.mkdir();m.u.mem_write(m.resident,m.resident_before);m.u.mem_write(m.video,snapshot);m.u.mem_write(m.video+v['patch_count'],struct.pack('<H',count))
 raw=bytearray(2048);rng=random.Random(488+count)
 for tile in range(32):
  for plane in range(3):
   for row in range(count):raw[tile*64+plane*16+row*2:tile*64+plane*16+row*2+2]=rng.randbytes(2)
  for row in range(count):raw[tile*64+48+row*2]=255
 m.u.mem_write(m.video+v['patch'],bytes(raw));assert m.call('nes_resident211_commit',[m.resident,1,905,0])==1
r={'passed':True,'scope':__doc__,'firmware_SHA256':sha(a.arm/'obj-nes-100/firmware.stm'),'rows':m.rows[1:],'semantic_HDMA_fixture':False}
(a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':True,'cases':8}))
