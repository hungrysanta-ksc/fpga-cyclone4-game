# SPDX-License-Identifier: MIT
"""Keep source367 rejection/ACK guards and validate causal frontier completion."""
import argparse,binascii,json,struct,sys
from pathlib import Path
from probe_nes_arm264 import ARM
from nes_delta231 import ROOT,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--states',type=Path,required=True);p.add_argument('--unused-reference',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 import guard_nes_source367 as prior
 sys.argv=[sys.argv[0],'--source',str(a.source),'--out',str(d/'retained367')];prior.main()
 state=json.loads((a.states/'replay368.json').read_text())['snapshots'];item=next(x for x in state if x['serial']==5)
 blob=(a.states/item['name']).read_bytes();old=ARM(a.states/'output.elf',None);arm=ARM(a.source/'output.elf',None)
 for name,size in [('receiver280',28),('resident285',6016),('history286',4910),('geometry_groups367',4)]:
  offset=old.symbols[name]-0x20000000;arm.uc.mem_write(arm.symbols[name],blob[offset:offset+size])
 at=arm.symbols['resident285'];resident=bytes(arm.uc.mem_read(at,6016));active=resident[3182]
 def packet():
  n=arm.call('source_hint367',[]);assert n==28
  p=bytes(arm.uc.mem_read(arm.call('source_buffer367',[]),28));assert binascii.crc_hqx(p[:26],65535)==int.from_bytes(p[26:],'little')
  return list(struct.unpack('<7H',p[12:26]))
 assert packet()==[0x213,0x218,0x216]+[0x213]*4
 assert bytes(arm.uc.mem_read(at,6016))==resident
 cases=[]
 for name,offset,value in [('unused_prior',2848+89//8,bytes([resident[2848+89//8]&~(1<<(89%8))])),
  ('inactive_prior',2560+active*144+89//8,bytes([resident[2560+active*144+89//8]&~(1<<(89%8))])),
  ('already_in_target',2560+(1-active)*144+89//8,bytes([resident[2560+(1-active)*144+89//8]|(1<<(89%8))])),
  ('invalid_prior_tag',89*2,b'\xff\xff')]:
  arm.uc.mem_write(at,resident);arm.uc.mem_write(at+offset,value);tags=packet()
  assert tags==[0x213,0x218]+[0x213]*5,(name,tags);cases.append(name)
 # A new higher-priority causal deficit wins, but cannot extend beyond3.
 arm.uc.mem_write(at,resident);arm.uc.mem_write(at+90*2,(8190).to_bytes(2,'little'));arm.uc.mem_write(at+3178,(91).to_bytes(2,'little'))
 off=2848+90//8;arm.uc.mem_write(at+off,bytes([resident[off]|(1<<(90%8))]))
 for bank,valid in [(active,True),(1-active,False)]:
  off=2560+bank*144+90//8;b=resident[off];arm.uc.mem_write(at+off,bytes([b|(1<<(90%8)) if valid else b&~(1<<(90%8))]))
 assert packet()==[0x213,0x218,8190]+[0x213]*4;cases.append('bounded3')
 unused=None
 if a.unused_reference:
  reference=a.unused_reference;prior_image=ARM(reference/'output.elf',None);arm=ARM(a.source/'output.elf',None);arm.call('reset280',[])
  for frame in range(905,911):
   for t in json.loads((reference/f'arm{frame}.json').read_text())['transfers']:
    if t.get('source_phase367')==2 and t['rx']:
     rx=bytes.fromhex(t['rx']);arm.uc.mem_write(arm.symbols['geometry_groups367'],bytes(4));arm.uc.mem_write(0x20028000,rx[:-2])
     assert arm.call('block286',[0x20028000,len(rx)-2,int.from_bytes(rx[-2:],'big')])==1
  snapshot=next(reference.glob('causal368-6-*.bin'));raw=snapshot.read_bytes();offset=prior_image.symbols['resident285']-0x20000000
  arm.uc.mem_write(arm.symbols['resident285'],raw[offset:offset+6016]);assert arm.call('source_hint367',[])==0
  unused=dict(frame=910,unused_hint_bytes=0,snapshot=sha(snapshot));cases.append('no_unused_retained_hint')
 result=dict(passed=True,retained=28+9,frontier_cases=cases,unused=unused,ELF=sha(a.source/'output.elf'),
  pins={str(p):sha(p) for p in (a.source/'output.elf',a.states/'output.elf',a.states/item['name'],Path(__file__).resolve())})
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
