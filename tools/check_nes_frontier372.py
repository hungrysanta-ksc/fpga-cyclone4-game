# SPDX-License-Identifier: MIT
"""Actual M4 source replay, exhaustive byte masks and overlap copies vs370."""
import argparse,json,random,struct
from pathlib import Path
from profile_nes_prepare353 import Profile
from check_nes_compact354 import objects
from nes_delta231 import BASE,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--hint-reference',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 old=BASE/'probes/nes-source370/joint02';elf=a.candidate/'output.elf';pins={str(x):sha(x) for x in (old/'output.elf',elf,Path(__file__).resolve())}
 syms=objects(old/'output.elf');assert syms==objects(elf)
 arms=[Profile(x) for x in (old/'output.elf',elf)];rows=[]
 for arm in arms:arm.call('reset280',[])
 def state(arm):return {n:bytes(arm.uc.mem_read(at,size)) for n,(at,size) in syms.items()}
 for frame in range(905,915):
  path=old/f'arm{frame}.json';pins[str(path)]=sha(path)
  blocks=[bytes.fromhex(t['rx']) for t in json.loads(path.read_text())['transfers'] if t.get('source_phase367')==2 and t['rx']]
  for i,b in enumerate(blocks):
   results=[]
   for arm in arms:
    arm.uc.mem_write(0x20028000,b[:-2]);arm.uc.mem_write(arm.symbols['geometry_groups367'],bytes(4));arm.instructions=0;arm.counts.clear();arm.pcs.clear()
    ok=arm.call('block286',[0x20028000,len(b)-2,int.from_bytes(b[-2:],'big')]);results.append((ok,state(arm),arm.instructions,dict(arm.counts)))
   assert results[0][:2]==results[1][:2] and results[0][0]==1,(frame,i)
   rows.append(dict(frame=frame,block=i,before=results[0][2],after=results[1][2],saved=results[0][2]-results[1][2],exclusive_before=results[0][3],exclusive_after=results[1][3]))
 # A mask byte's high tail bits,zero mask,raw>=64 and odd base retain exact
 # reject state/history. Sparse raw dirty bits are accumulated once per8B.
 rng=random.Random(372);seed=bytes(rng.randrange(64) for _ in range(4910));direct=[]
 def compare(packet,index,raw=False,odd=0):
  result=[];base=0x20010000+odd
  for arm in arms:
   s=bytearray(28);struct.pack_into('<HHh',s,14,1,512,67 if raw else -1);s[21]=2 if raw else 1;struct.pack_into('<H',s,8,65535)
   arm.uc.mem_write(arm.symbols['receiver280'],bytes(s));arm.uc.mem_write(arm.symbols['source_groups352'],bytes(4));arm.uc.mem_write(arm.symbols['geometry_groups367'],bytes(4))
   arm.uc.mem_write(base,seed);arm.uc.mem_write(0x20028000,packet);ok=arm.call('feed280',[base,0x20028000,len(packet)])
   result.append((ok,bytes(arm.uc.mem_read(base,4910)),bytes(arm.uc.mem_read(arm.symbols['receiver280'],28)),bytes(arm.uc.mem_read(arm.symbols['source_groups352'],4)),bytes(arm.uc.mem_read(arm.symbols['geometry_groups367'],4))))
  assert result[0]==result[1],(index,raw,odd,packet.hex())
  direct.append(bool(result[0][0]))
 for index,length in ((0,66),(31,66),(32,64),(67,46),(68,64)):
  mb=(length+7)//8
  for at in (0,mb-1):
   for mask in range(256):
    masks=bytearray(mb);masks[at]=mask;values=bytes((i*7+3)%64 for i in range(mask.bit_count()))
    compare(bytes([index])+masks+values,index,index==68,mask&1)
  if index==68:compare(bytes([68,3])+bytes(7)+bytes([1,64]),68,True)
 for g in (0,1,31):
  for direction in (1,255):
   for odd in (0,1):compare(bytes([128|g,direction,254,129]),g,False,odd)
 hints=[];hint_ref=a.hint_reference or old/'output.elf';pins[str(hint_ref)]=sha(hint_ref);hint_arm=Profile(hint_ref);hint_syms=objects(hint_ref)
 for frame in range(907,915):
  file=next(old.glob(f'causal368-{frame-904}-*.bin'));pins[str(file)]=sha(file);packets=[]
  blob=file.read_bytes();costs=[]
  for arm in (hint_arm,arms[1]):
   targets=hint_syms if arm is hint_arm else syms
   for name,(at,size) in targets.items():
    if name in syms:
     previous,nbytes=syms[name];assert nbytes==size;arm.uc.mem_write(at,blob[previous-0x20000000:previous-0x20000000+size])
   arm.instructions=0;n=arm.call('source_hint367',[]);assert n in (0,28);costs.append(arm.instructions)
   at=arm.call('source_buffer367',[]);packets.append(bytes(arm.uc.mem_read(at,n)))
  assert packets[0]==packets[1];hints.append(dict(frame=frame,reference_instructions=costs[0],after=costs[1],packet=packets[1].hex()))
 result=dict(passed=True,rows=rows,first_blocks=[x for x in rows if x['block']==0],direct_cases=len(direct),direct_accepted=sum(direct),hints_exact=hints,objects=len(syms),new_timing=False,pins=pins)
 assert not a.out.exists();a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,first914=[x for x in rows if x['frame']==914 and x['block']==0],direct=len(direct)),indent=2))
if __name__=='__main__':main()
