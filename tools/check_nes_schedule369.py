# SPDX-License-Identifier: MIT
"""Compare actual M4 steps and direct descriptor admission against NES368."""
import argparse,json,random,struct
from pathlib import Path
from probe_nes_arm264 import ARM
from check_nes_compact354 import objects
from nes_delta231 import sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--profile',type=Path,required=True)
 p.add_argument('--candidate',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 d=a.profile;old=d/'output.elf';new=a.candidate/'output.elf';syms=objects(old)
 assert syms==objects(new),'Snapshot ABI changed'
 report=json.loads((d/'profile369.json').read_text());rows=[];direct=[]
 pins={str(p):sha(p) for p in (old,new,d/'profile369.json',Path(__file__))}
 def fresh(elf,data):
  arm=ARM(elf,None);arm.uc.mem_write(0x20000000,data);return arm
 def state(arm):return {n:bytes(arm.uc.mem_read(at,size)) for n,(at,size) in syms.items()}
 for x in report['rows']:
  file=d/x['snapshot'];pins[str(file)]=sha(file);data=file.read_bytes();results=[]
  for elf in (old,new):
   arm=fresh(elf,data);ok=arm.call('next_step286',[])
   results.append((ok,state(arm),arm.instructions))
  assert results[0][:2]==results[1][:2],('step state/result',x['index'])
  assert results[0][2]==x['instructions'],('original count',x['index'])
  rows.append(dict(index=x['index'],result=results[0][0],before=results[0][2],after=results[1][2],saved=results[0][2]-results[1][2]))
 rng=random.Random(369)
 for index in (0,1,5,24,29):
  data=(d/f'row369-{index}.bin').read_bytes()
  for test in range(64):
   tag=(0x213,0x218,0x216,8191)[test%4];kind=test%4;mask=255 if test%3 else 127
   row=[i//2 for i in range(16)];alt=[65535]*8
   if test&8:row[test%16]^=1
   if test&16:alt[test%8]=tag
   gen=5 if test%5 else 4
   q=struct.pack('<HHHBB16B8H',gen,0,tag,kind,mask,*row,*alt)
   exact=tag|0x1fed6c8da4480000 if test%2 else rng.getrandbits(64)
   results=[]
   for elf in (old,new):
    arm=fresh(elf,data);at=0x20028000;arm.uc.mem_write(at,q)
    # AAPCS: r0/r1 are pointers, r2/r3 carry the aligned uint64 key,
    # and the fifth argument is at the caller's initial SP.
    arm.uc.mem_write(0x2003f000,struct.pack('<I',at))
    ok=arm.call('nes_resident211_slot',[arm.symbols['resident285'],arm.symbols['video285'],exact&0xffffffff,exact>>32])
    results.append((ok,state(arm),bytes(arm.uc.mem_read(at,len(q)))))
   assert results[0]==results[1],('descriptor state/result',index,test)
   direct.append(dict(snapshot=index,test=test,kind=kind,generation=gen,result=results[0][0]))
 stops=[]
 for index in (0,1,5,24,29):
  data=(d/f'row369-{index}.bin').read_bytes();results=[]
  for elf in (old,new):
   arm=fresh(elf,data);arm.call('stop286',[])
   assert arm.call('next_step286',[])==0 and arm.call('commit285',[])==0
   results.append(state(arm))
  assert results[0]==results[1],('STOP invalidation',index)
  stops.append(dict(snapshot=index,late_step_rejected=True,commit_rejected=True,exact_state=True))
 result=dict(passed=True,new_timing=False,global_objects=len(syms),rows=rows,direct_cases=direct,STOP_cases=stops,total_saved=sum(x['saved'] for x in rows),pins=pins)
 a.out.parent.mkdir(parents=True,exist_ok=True);assert not a.out.exists()
 a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
 print(json.dumps(dict(passed=True,steps=len(rows),direct_cases=len(direct),STOP_cases=len(stops),total_saved=result['total_saved'])))
if __name__=='__main__':main()
