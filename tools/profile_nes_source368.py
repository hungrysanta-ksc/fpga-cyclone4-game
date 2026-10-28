# SPDX-License-Identifier: MIT
"""Differential M4 source/hint profiles using causally recovered states."""
import argparse,binascii,json,random,struct
from pathlib import Path
from probe_nes_arm264 import ARM
from nes_delta231 import BASE,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();d=a.root.resolve()
 replay=d/'replay01';reference=BASE/'probes/nes-hint367/long02';ref=ARM(reference/'output.elf',None)
 names={'baseline':reference/'output.elf','hint':d/'hint02/output.elf','joint':d/'joint05/output.elf'}
 states=json.loads((replay/'replay368.json').read_text())['snapshots'];hints=[];decode=[]
 for variant,elf in names.items():
  arm=ARM(elf,None)
  for serial in (3,4,5):
   state=next(x for x in states if x['serial']==serial);blob=(replay/state['name']).read_bytes()
   for name,size in [('receiver280',28),('resident285',6016),('history286',4910),('geometry_groups367',4)]:
    off=ref.symbols[name]-0x20000000;arm.uc.mem_write(arm.symbols[name],blob[off:off+size])
   before=arm.instructions;n=arm.call('source_hint367',[]);cost=arm.instructions-before;assert n==28
   address=arm.call('source_buffer367',[]);packet=bytes(arm.uc.mem_read(address,28));tags=list(struct.unpack('<7H',packet[12:26]))
   assert binascii.crc_hqx(packet[:26],65535)==int.from_bytes(packet[26:],'little')
   if serial==5 and variant!='baseline':assert tags==[0x213,0x218,0x216]+[0x213]*4
   hints.append(dict(variant=variant,frame=904+serial,instructions=cost,tags=tags))
  arm=ARM(elf,None);arm.call('reset280',[])
  for frame in range(905,910):
   tr=json.loads((reference/f'arm{frame}.json').read_text())['transfers'];blocks=[]
   for t in tr:
    if t.get('source_phase367')==2 and t['rx']:
     rx=bytes.fromhex(t['rx']);blocks.append(rx)
   for i,rx in enumerate(blocks):
    arm.uc.mem_write(0x20028000,rx[:-2]);before=arm.instructions
    assert arm.call('block286',[0x20028000,len(rx)-2,int.from_bytes(rx[-2:],'big')])==1
    decode.append(dict(variant=variant,frame=frame,block=i,bytes=len(rx)-2,instructions=arm.instructions-before,
     state=bytes(arm.uc.mem_read(arm.symbols['receiver280'],28)).hex(),history=__import__('hashlib').sha256(bytes(arm.uc.mem_read(arm.symbols['history286'],4910))).hexdigest()))
 # Every intermediate decoder state and history must match the old CRC path.
 base=[x for x in decode if x['variant']=='baseline']
 for variant in ('hint','joint'):
  for x,y in zip(base,[x for x in decode if x['variant']==variant]):
   assert (x['frame'],x['block'],x['state'],x['history'])==(y['frame'],y['block'],y['state'],y['history'])
 arm=ARM(names['joint'],None);rng=random.Random(368);vectors=[(c,b) for c in (0,1,0x1234,65535) for b in range(256)]+[(rng.randrange(65536),rng.randrange(256)) for _ in range(256)]
 for c,b in vectors:assert arm.call('crc_source368',[c,b])==binascii.crc_hqx(bytes([b]),c)
 result=dict(passed=True,new_timing=False,CRC_vectors=len(vectors),hints=hints,decode=decode,
  pins={str(p):sha(p) for p in [*names.values(),replay/'replay368.json',Path(__file__).resolve()]})
 (d/'profile368.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(hints=hints,CRC_vectors=len(vectors)),indent=2))
if __name__=='__main__':main()
