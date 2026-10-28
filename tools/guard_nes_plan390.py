# SPDX-License-Identifier: MIT
"""Execute the M4 planner on independent sparse/column/dense coverage vectors."""
import argparse,json,random,struct
from pathlib import Path
from probe_nes_arm264 import ARM
from nes_delta231 import BASE,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);unit=BASE/'probes/nes-plan390/arm01/unit.elf';rng=random.Random(390);rows=[]
 masks=[set(),set(range(2048)),{0,31,32,1023,1024,2047},set(range(31,100)),set(range(0,2048,32)),set(range(0,2048,7))]
 masks += [set(rng.sample(range(2048),n))for n in (1,2,7,16,64,127,255,512)*3]
 for case,dirty in enumerate(masks):
  bits=bytearray(256)
  for w in dirty:bits[w//8]|=1<<(w%8)
  arm=ARM(unit,None);arm.symbols.update(io259=0x0800f000,trace259=0x0800f004);arm.uc.mem_write(arm.symbols['bits390'],bytes(bits));arm.call('reset_plan390',[]);steps=0
  while True:
   n=arm.call('step_plan390',[arm.symbols['packet390']]);steps+=1
   if n:break
   assert steps<=20
  b=bytes(arm.uc.mem_read(arm.symbols['packet390'],n));mode=b[3];ranges=int.from_bytes(b[12:14],'little');words=int.from_bytes(b[14:16],'little');assert words==len(dirty)
  expected=[]
  for w in sorted(dirty):
   if expected and expected[-1][0]+expected[-1][1]==w and expected[-1][1]<32:expected[-1][1]+=1
   else:expected.append([w,1])
  assert ranges==len(expected)
  if mode==0:
   coords=[list(struct.unpack_from('<HH',b,i))for i in range(16,n,4)];assert coords==expected and n<=44
  elif mode==1:
   assert n==144
   for col in range(64):
    actual=[(w//32)%32 for w in dirty if (w&31)+32*(w//1024)==col];lo,hi=b[16+col*2:18+col*2];assert (lo,hi)==((min(actual),max(actual))if actual else(32,0))
  else:assert mode==2 and n==16
  rows.append(dict(case=case,words=words,ranges=ranges,mode=mode,bytes=n,steps=steps,instructions=arm.instructions,observed_stack=0x2003f000-arm.low_sp))
 assert {r['mode']for r in rows}=={0,1,2}
 (d/'result.json').write_text(json.dumps(dict(passed=True,cases=rows,unit=sha(unit),source=sha(Path(__file__))),indent=2)+'\n');print(json.dumps(dict(passed=True,cases=len(rows),max_stack=max(r['observed_stack']for r in rows))))
if __name__=='__main__':main()
