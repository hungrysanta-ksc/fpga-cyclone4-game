"""Execute full-linked serializers; compare every short padding length.

Exact wire bytes versus732B, independent expanded bytes, all caller offsets,
and existing expanded-op NULL rejection. Transport here is a callback fixture;
the two complete replays execute the actual credit/SPI and65816 consumer.
"""
import argparse,json,hashlib
from pathlib import Path
from check_nes_reuse635_arm import Sender
from nes_raw506 import sha

def run(a):
 machines=[Sender(p,'normal') for p in (a.base,a.arm)]
 sink=0x20015800;data=0x20016800;outputs=[];cost=[]
 for index,m in enumerate(machines):
  m.u.mem_write(data,bytes(240));rows={};counts={}
  for n in range(1,241):
   m.call('nes_sink165_reset',[sink,m.callback|1,0]);m.heads=[]
   for k,v,size in [('enqueue',m.callback|1,4),('serial',48,4),('generation',952,2),('state',1,1)]:m.put(sink,'nes_native_sink165',k,v,size)
   before=m.instructions
   assert m.call('packet_wire',[sink,2,5,1121-n,data if index==0 else 0,n,0])
   counts[n]=m.instructions-before
   assert len(m.heads)==1
   b=m.heads[0];raw=b[16:]
   if b[0]==4:
    assert n>=4 and n%2==0 and len(raw)==2
    assert int.from_bytes(b[14:16],'little')==n
    raw*=n//2
   else:assert b[0]==2 and (n<4 or n%2==1)
   assert raw==bytes(n) and int.from_bytes(b[10:12],'little')==1121-n
   rows[n]=b
  outputs.append(rows);cost.append(counts)
 assert outputs[0]==outputs[1]
 # Every possible caller tail: >240B emits even extended repeat, then at
 # most one short tail. Odd short tails must remain one literal packet.
 for offset in range(1122):
  at=offset;restored=bytearray()
  while at<1121:
   n=1121-at
   if n>240:n&=~1;restored.extend(bytes(n))
   else:
    b=outputs[1][n];restored.extend(b[16:]*(n//2) if b[0]==4 else b[16:])
   at+=n
  assert len(restored)==1121-offset and not any(restored)
 m=machines[1];rejections=[]
 for op,section,n,expanded in [(5,5,2,242),(6,2,2,256),(7,0,4,16),(8,4,4,8),(2,5,241,0)]:
  m.call('nes_sink165_reset',[sink,m.callback|1,0]);m.heads=[]
  assert not m.call('packet_wire',[sink,op,section,0,0,n,expanded]) and not m.heads
  rejections.append([op,section,n,expanded])
 r=dict(stage=733,passed=True,scope=__doc__,base=sha(a.base/'obj-nes-100/firmware.stm'),firmware=sha(a.arm/'obj-nes-100/firmware.stm'),exact_short_lengths=240,caller_offsets=1122,invalid_cases=rejections,wire_sha256=hashlib.sha256(b''.join(outputs[1].values())).hexdigest(),instruction_delta={n:cost[1][n]-cost[0][n] for n in range(1,241)})
 a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
 print('PASS733:240 exact linked packets;1122 caller offsets;5 invalid source/length guards')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','arm','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
