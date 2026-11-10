"""Actual linked span equivalence and owned-bulk ordinary admission guards."""
import argparse,json,random
from pathlib import Path
from check_nes_supply485_arm import ARM,Endpoint,crc
from check_nes_game478 import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_PC,UC_ARM_REG_LR
from nes_raw506 import sha
from check_nes_reuse635_arm import Sender

class Span(ARM):
 def hook(self,u,at,size,user):
  if at==getattr(self,'syms',{}).get('packet_wire'):
   sp=u.reg_read(UC_ARM_REG_SP);ptr,n,expanded=[int.from_bytes(u.mem_read(sp+i*4,4),'little') for i in range(3)]
   self.packets.append([u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R2),u.reg_read(UC_ARM_REG_R3),bytes(u.mem_read(ptr,n)).hex(),expanded])
   u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  super().hook(u,at,size,user)

def spans(base,arm):
 machines=[Span(p,'normal') for p in (base,arm)];rng=random.Random(729);rows=[]
 for n in (1,2,3,4,31,32,63,64,65,128,192,240,241,256,384,544,1121,2048,4096):
  raw=bytes(rng.randrange(256) for _ in range(n))
  for kind,b in [('random',raw),('byte',bytes([19])*n),('word',(b'\x12\x34'*(n//2+1))[:n]),('edge',raw[:min(65,n)]+bytes(n-min(65,n)))]:
   outputs=[]
   for m in machines:
    m.packets=[];m.u.mem_write(0x20010000,b)
    assert m.call('span',[m.s,5,0,0x20010000,n])
    restored=b''.join(bytes.fromhex(p[3])*(p[4]//2) if p[0]==5 else bytes.fromhex(p[3]) for p in m.packets)
    assert restored==b and sum(len(bytes.fromhex(p[3])) if p[0]!=5 else p[4] for p in m.packets)==n
    outputs.append(m.packets)
   assert outputs[0]==outputs[1],(n,kind)
   rows.append(dict(length=n,kind=kind,packets=len(outputs[0])))
 return rows

def owned(arm,name):
 m=ARM(arm,'normal');m.setup();e=m.endpoint
 for k,v,n in [('started',1,1),('ending',1,1),('generation',907,2)]:m.put(m.p,'nes_plan200',k,v,n)
 e.jobs=[(1,0,32,1)]
 assert m.call('nes_plan200_progress',[m.p,0]) and m.get(m.p,'nes_plan200','bulk_pending')
 before=len(e.calls);mode=0
 if name in ('FINAL','MAP','HDMA'):mode={'FINAL':1,'MAP':2,'HDMA':3}[name]
 if name.startswith('credit'):
  used=int(name[-1]);m.put(m.w,'nes_sink_window184','sent',used,2);m.put(m.w,'nes_sink_window184','retired',0,2)
 if name=='wrap':
  m.put(m.w,'nes_sink_window184','sent',0,2);m.put(m.w,'nes_sink_window184','retired',65535,2)
 if name=='STOP':e.mode='STOP_after_bulk'
 if name=='wrong_generation':m.put(m.p,'nes_plan200','generation',908,2)
 if name=='no_owner':m.put(m.p,'nes_plan200','bulk_pending',0,1)
 if name=='pending_E9':m.put(m.p,'nes_plan200','count',1,1)
 # If a path must query, corrupt that actual response. Early ordinary credit
 # may bypass this unobserved response; FINAL must eventually reject it.
 old=e.exchange
 def exchange(tx,t):
  r=old(tx,t)
  if tx[0]==0xe8:r=r[:-1]+bytes([r[-1]^1])
  return r
 e.exchange=exchange
 ok=m.call('nes_plan200_progress',[m.p,mode])
 expected=name in ('normal','credit0','credit1','credit2','wrap')
 assert bool(ok)==expected,(name,ok)
 if expected:assert len(e.calls)==before and m.get(m.p,'nes_plan200','bulk_pending')
 assert not m.get(m.s,'nes_native_sink165','displayed')
 assert not m.call('nes_plan200_retire',[m.p]) and not e.rearmed
 if expected:assert not m.call('nes_plan200_progress',[m.p,1]),'FINAL bypassed CRC'
 return dict(case=name,ordinary_admitted=bool(ok),final_ACK_granted=False,passed=True)

class Ordinary(Endpoint):
 def advance(self,clock):
  while self.pending and self.pending[0][0]<=clock:
   _,b=self.pending.pop(0)
   if b[0]==7:self.jobs.pop(0)
   self.retired+=1;self.last=bytes([0,b[0]])+b[2:10]+b'\x65\x9a'
 def exchange(self,tx,clock):
  if tx[0]==0xe1 and tx[1]==2:
   self.advance(clock);b=tx[1:-2];self.calls.append(tx.hex())
   assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
   assert b[1]==5 and b[16:]==bytes(range(16)) and int.from_bytes(b[2:4],'little')==self.sent and self.sent-self.retired<4
   self.sent+=1;self.pending.append((clock+1000000,b));return bytes(len(tx))
  return super().exchange(tx,clock)

def queued(arm,stop):
 m=ARM(arm,'normal');m.endpoint=Ordinary();m.setup();e=m.endpoint
 m.put(m.s,'nes_native_sink165','plan',m.p,4)
 for k,v,n in [('started',1,1),('ending',1,1),('generation',907,2)]:m.put(m.p,'nes_plan200',k,v,n)
 e.jobs=[(1,0,32,1)]
 assert m.call('nes_plan200_progress',[m.p,0]) and e.bulk==1
 e.pending=[(100000000,b) for _,b in e.pending];before=len(e.calls)
 m.u.mem_write(m.q,bytes(range(16)))
 assert m.call('span',[m.s,5,0,m.q,16])
 if stop:e.mode='STOP_after_bulk'
 assert bool(m.call('span',[m.s,5,16,m.q,16]))==(not stop)
 sent=2 if stop else 3
 assert e.sent==sent and e.retired==0 and all(x.startswith('e1') for x in e.calls[before:])
 assert m.get(m.p,'nes_plan200','bulk_pending') and not m.get(m.s,'nes_native_sink165','displayed')
 if not stop:
  e.pending=[(0,b) for _,b in e.pending];e.end=True
  assert m.call('nes_plan200_progress',[m.p,1]) and e.retired==3
 assert not m.call('nes_plan200_retire',[m.p]) and not e.rearmed
 return dict(STOP=stop,packets=sent,reserved_credit=True,final_display_ACK=False,passed=True)

def oam(base,arm):
 rng=random.Random(729);random_bytes=bytes(rng.randrange(256) for _ in range(544));rows=[]
 vectors=[bytes(544),(b'\x12\x34'*272),random_bytes]
 for length in (60,64,68,256,512):vectors.append(random_bytes[:512-length]+b'\x01\x23\x45\x67'*(length//4)+random_bytes[512:])
 for i,b in enumerate(vectors):
  packets=[];counts=[]
  for src in (base,arm):
   m=Sender(src,'normal');m.heads=[];m.test_sink=sink=0x20015800
   for k,v,n in [('serial',48,4),('generation',952,2),('displayed',1,1),('state',1,1),('enqueue',m.callback|1,4),('exchange',m.callback|1,4)]:m.put(sink,'nes_native_sink165',k,v,n)
   for k,v,n in [('prepared',1,1),('open',1,1),('displayed',1,1),('serial',48,4),('generation',952,2),('target',1,1)]:m.put(m.resident,'nes_resident211',k,v,n)
   for k,v,n in [('valid',1,1),('generation',952,2),('bg_count',1,2),('obj_count',16,2),('hdma_size',21,2),('display_mask',0x1e,1)]:m.put(m.video,'nes_native_video165',k,v,n)
   m.u.mem_write(m.video+m.layout['nes_native_video165']['oam'],b);before=m.instructions
   assert m.call('nes_sink212_seal',[sink,m.video,m.resident,4192])
   counts.append(m.instructions-before);packets.append(m.heads)
   restored=bytearray(544);seen=set()
   for h in m.heads:
    if h[1]!=4:continue
    off=int.from_bytes(h[10:12],'little');raw=h[16:];n=int.from_bytes(h[14:16],'little')
    if h[0] in (4,5,8):raw=raw*(n//len(raw))
    for j in range(off,off+len(raw)):assert j not in seen;seen.add(j)
    restored[off:off+len(raw)]=raw
   assert restored==b and len(seen)==544,(i,str(src),[(h[0],h[1],h[10:16].hex()) for h in m.heads])
  assert packets[0]==packets[1],i
  rows.append(dict(case=i,identical_packets=True,instructions=counts))
 return rows

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','arm','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();r=dict(passed=True,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),span=spans(a.base,a.arm),owned=[owned(a.arm,n) for n in ('normal','credit0','credit1','credit2','credit3','credit4','wrap','STOP','wrong_generation','no_owner','pending_E9','FINAL','MAP','HDMA')],queued=[queued(a.arm,stop) for stop in (False,True)],oam=oam(a.base,a.arm),scope=__doc__)
 a.out.write_text(json.dumps(r,indent=2)+'\n');print('PASS729',len(r['span']),'span equivalence,',len(r['owned']),'owned credit/STOP/FINAL guards')
