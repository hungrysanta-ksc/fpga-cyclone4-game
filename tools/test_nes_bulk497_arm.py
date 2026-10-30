# SPDX-License-Identifier: MIT
"""497 linked M4 E9/E8/E0 over bounded two-bank/coalesced endpoint.
Instruction clock and allocated consumer delay; not physical ARM/IRQ/ROM timing.
"""
import argparse,json,struct,collections
from pathlib import Path
import check_nes_supply485_arm as base
from check_nes_game478 import crc,sha
class Endpoint(base.Endpoint):
 def __init__(self,mode='normal'):
  super().__init__(mode);self.todo=[];self.open=None;self.groups=[];self.events=[];self.max_banks=0;self.delay=12000
 def advance(self,clock):
  super().advance(clock)
  while self.todo:
   q=self.todo[0]
   if q is None:
    if self.open:self.publish()
    self.todo.pop(0);self.end=True;break
   kind,slot,size=q
   if self.open and not(self.open[0]==kind and self.open[1]+self.open[2]==slot and self.open[2]+size<=2048):self.publish()
   if self.open is None:
    if len(self.jobs)==2:break
    self.open=[kind,slot,0,self.token];self.token+=1
   self.open[2]+=size;self.todo.pop(0)
   self.max_banks=max(self.max_banks,len(self.jobs)+int(self.open is not None));assert self.max_banks<=2
 def publish(self):
  self.jobs.append(tuple(self.open));self.groups.append(tuple(self.open));self.open=None
 def exchange(self,tx,clock):
  op=tx[0];self.advance(clock)
  if op==0xe9:
   self.calls.append(tx.hex());n=int.from_bytes(tx[1:3],'little');assert len(tx)==n+8 and not self.todo
   assert crc(tx[:n+6],8,7,0)==tx[n+6] and crc(tx[4:4+n],16,0x1021,65535)==int.from_bytes(tx[n+4:n+6],'big') and tx[-1]==165
   at=4;count=0
   while at<4+n:
    kind=tx[at]&3
    if tx[at]&128:
     assert tx[at]&252==128;gen=int.from_bytes(tx[at+1:at+3],'little');slot=int.from_bytes(tx[at+3:at+5],'little')if kind<2 else 0;length=7 if kind==0 else 8 if kind==1 else 3
    else:
     gen=int.from_bytes(tx[at+2:at+4],'little');slot=int.from_bytes(tx[at+4:at+6],'little');length=16+2*tx[at+1].bit_count();assert tx[at+15]==1
    assert gen==self.generation
    self.todo.append(None if kind==3 else (int(kind==1),slot*(32 if kind==1 else 16),32 if kind==1 else 16));at+=length;count+=1
   assert at==4+n and count==tx[3];self.accepted+=1;reply=bytes(len(tx))
  else:
   if op==0xe1:assert not self.pending,'second bulk submitted before first ACK'
   reply=super().exchange(tx,clock)
   if op==0xe1:self.pending[-1]=(clock+self.delay,self.pending[-1][1])
   if op==0xe8 and not self.jobs and not self.stale_reads and self.todo:
    r=bytearray(reply);r[3]=0;r[19]=crc(r[1:19],8,7,0);reply=bytes(r)
  self.events.append({'instruction':clock,'op':hex(op),'accepted_E9':self.accepted,'sent':self.sent,'retired':self.retired,'banks':len(self.jobs)+int(self.open is not None),'queued_plans':len(self.todo)})
  return reply
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['arm','plans','out']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(exist_ok=False);base.Endpoint=Endpoint;rows=[];pins={}
 for delay in [0,12000,100000]:
  for frame in range(905,917):
   m=base.ARM(a.arm,'normal');m.setup();e=m.endpoint;e.generation=frame;e.delay=delay;m.put(m.s,'nes_native_sink165','generation',frame,2)
   path=a.plans/f'frame{frame}/plans.json';pins[str(frame)]=sha(path);plans=json.loads(path.read_text());expected=[]
   for bank,h in plans:
    q=bytes.fromhex(h);gen,slot,tag,kind,mask=struct.unpack_from('<HHHBB',q);size=32 if kind==1 else 16;k=int(kind==1)
    if expected and expected[-1][0]==k and expected[-1][1]+expected[-1][2]==slot*size and expected[-1][2]+size<=2048:expected[-1][2]+=size
    else:expected.append([k,slot*size,size])
    m.u.mem_write(m.q,q);assert m.call('nes_plan200_emit',[m.p,m.q]),(frame,'emit',e.events[-4:])
   assert m.call('nes_plan200_finish',[m.p]),(frame,'finish',e.events[-4:])
   assert [list(x[:3])for x in e.groups]==expected and e.sent==e.retired==len(expected) and not e.jobs and not e.todo and not e.open
   assert not m.get(m.p,'nes_plan200','bulk_pending') and not m.get(m.s,'nes_native_sink165','displayed')
   before=len(e.calls);assert m.call('nes_plan200_retire',[m.p])==0 and not e.rearmed and len(e.calls)==before
   (a.out/f'events-{frame}-{delay}.json').write_text(json.dumps(e.events)+'\n')
   rows.append({'frame':frame,'delay_instructions':delay,'plans':len(plans),'chunks':len(expected),'max_banks':e.max_banks,'instructions':m.instructions,'wire_B':sum(len(bytes.fromhex(x))for x in e.calls),'op_counts':dict(collections.Counter(hex(bytes.fromhex(x)[0])for x in e.calls))})
 negatives=[]
 for mode in ['bad_E8_CRC','wrong_generation','same_token_mutation','old_token','bad_ACK','bad_accepted','STOP_after_E9','STOP_after_bulk','ambiguous_E1']:
  m=base.ARM(a.arm,mode);m.setup();m.endpoint.generation=905;m.put(m.s,'nes_native_sink165','generation',905,2);ok=True
  for bank,h in json.loads((a.plans/'frame905/plans.json').read_text()):
   m.u.mem_write(m.q,bytes.fromhex(h))
   if not m.call('nes_plan200_emit',[m.p,m.q]):ok=False;break
  if ok:ok=bool(m.call('nes_plan200_finish',[m.p]))
  assert not ok and not m.get(m.s,'nes_native_sink165','displayed'),mode
  before=len(m.endpoint.calls);assert not m.call('nes_plan200_finish',[m.p]) and len(m.endpoint.calls)==before,mode
  negatives.append(mode)
 r={'passed':True,'scope':__doc__,'rows':rows,'negative_cases':negatives,'firmware_sha256':sha(a.arm/'obj-nes-100/firmware.stm'),'plans_sha256':pins,'single_bulk_pending_checked':True,'finish_after_all_consumed':True,'retire_without_display_ACK_rejected':True,'actual_SNES_CPU_connected':False,'physical_time':False}
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'cases':len(rows),'chunks_per_12frames':sum(x['chunks']for x in rows[:12]),'max_banks':max(x['max_banks']for x in rows)}))
