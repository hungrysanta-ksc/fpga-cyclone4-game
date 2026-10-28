# SPDX-License-Identifier: MIT
"""Count actual M4 tile calls at identical group snapshots, not new timing."""
import argparse,json
from pathlib import Path
from probe_nes_arm264 import ARM
from unicorn.arm_const import UC_ARM_REG_R1,UC_ARM_REG_R2
from nes_delta231 import sha

class Trace(ARM):
 def hook(self,uc,address,size,user):
  if address==(self.symbols['tile']&~1):self.lookups.append((uc.reg_read(UC_ARM_REG_R1),uc.reg_read(UC_ARM_REG_R2)))
  super().hook(uc,address,size,user)

def main():
 p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True)
 p.add_argument('--snapshots',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 images=(a.reference/'output.elf',a.candidate/'output.elf');rows=[];pins={str(p):sha(p) for p in (*images,Path(__file__))}
 for i in range(41):
  f=a.snapshots/f'row369-{i}.bin';pins[str(f)]=sha(f);data=f.read_bytes();results=[]
  for image in images:
   arm=Trace(image,None);arm.lookups=[];arm.uc.mem_write(0x20000000,data);ok=arm.call('next_step286',[])
   results.append(dict(result=ok,instructions=arm.instructions,BG=sum(k==1 for t,k in arm.lookups),OBJ=sum(k==2 for t,k in arm.lookups)))
  assert results[0]['result']==results[1]['result'] and results[0]['OBJ']==results[1]['OBJ']
  rows.append(dict(index=i,before=results[0],after=results[1]))
 total={n:{k:sum(x[n][k] for x in rows) for k in ('instructions','BG','OBJ')} for n in ('before','after')}
 assert total['before']['BG']==792 and total['after']['BG']==189
 assert total['before']['instructions']-total['after']['instructions']==55253
 result=dict(passed=True,new_timing=False,rows=rows,total=total,pins=pins)
 assert not a.out.exists();a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(total))
if __name__=='__main__':main()
