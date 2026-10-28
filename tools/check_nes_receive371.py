# SPDX-License-Identifier: MIT
"""Real warm M4 receiver/hints vs unchanged decoder state, with late faults."""
import argparse,json
from pathlib import Path
from guard_nes_receive371 import Receive
from probe_nes_arm264 import ARM,crc
from nes_delta231 import BASE,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 old=BASE/'probes/nes-source370/joint02';elf=a.source/'output.elf';ref=ARM(old/'output.elf',None);ref.call('reset280',[])
 def blocks(f):
  path=old/f'arm{f}.json';pins[str(path)]=sha(path)
  return [bytes.fromhex(t['rx'])[:-2] for t in json.loads(path.read_text())['transfers'] if t.get('source_phase367')==2 and t['rx']]
 def prior(arm,f):
  if f>=907:
   path=next(old.glob(f'causal368-{f-904}-*.bin'));pins[str(path)]=sha(path);blob=path.read_bytes()
   offset=ref.symbols['resident285']-0x20000000;arm.uc.mem_write(arm.symbols['resident285'],blob[offset:offset+6016])
 pins={str(elf):sha(elf),str(old/'output.elf'):sha(old/'output.elf'),str(Path(__file__).resolve()):sha(Path(__file__)),str(Path(__file__).with_name('guard_nes_receive371.py').resolve()):sha(Path(__file__).with_name('guard_nes_receive371.py'))};rows=[];saved=None
 arm=Receive(elf,blocks(905),'normal')
 for n in ('reset259','reset285','reset280'):arm.call(n,[])
 for f in range(905,915):
  arm.blocks=blocks(f);arm.at=0;arm.seen=False;arm.held=False;arm.acks=0;arm.credits=[];arm.hints=[]
  arm.call('source_reset367',[]);prior(arm,f);assert arm.call('source_receive367',[])==1
  for b in arm.blocks:
   ref.uc.mem_write(0x20028000,b);assert ref.call('block286',[0x20028000,len(b),crc(b)])==1
  for n,size in [('receiver280',28),('history286',4910)]:
   assert bytes(arm.uc.mem_read(arm.symbols[n],size))==bytes(ref.uc.mem_read(ref.symbols[n],size)),(f,n)
  assert arm.acks==1 and arm.at==len(arm.blocks) and not arm.held
  rows.append(dict(frame=f,blocks=len(arm.blocks),credits=len(arm.credits),semantic_before_credits=arm.credits,hints=arm.hints,exact_decoder_and_history=True))
  if f==906:saved=bytes(arm.uc.mem_read(0x20000000,0x40000))
 negative=[]
 assert next(x for x in rows if x['frame']==914)['semantic_before_credits'][:2]==[0,0]
 for mode in ('payload_crc','payload_crc_second','late_semantic','cancel_hint'):
  arm=Receive(elf,blocks(907),mode);arm.uc.mem_write(0x20000000,saved);arm.call('source_reset367',[]);prior(arm,907)
  assert arm.call('source_receive367',[])==0 and not arm.acks and not arm.held
  if mode=='payload_crc':assert not arm.credits and not arm.hints
  else:assert arm.credits and arm.hints
  if mode=='payload_crc_second':assert len(arm.credits)==1
  if arm.hints:assert arm.hints[0]['packet']==next(x for x in rows if x['frame']==907)['hints'][0]['packet']
  negative.append(dict(mode=mode,credits=len(arm.credits),hints=len(arm.hints),final_ACK=arm.acks))
 result=dict(passed=True,new_timing=False,rows=rows,late_faults=negative,pins=pins)
 assert not a.out.exists();a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,frames=len(rows),late_faults=negative)))
if __name__=='__main__':main()
