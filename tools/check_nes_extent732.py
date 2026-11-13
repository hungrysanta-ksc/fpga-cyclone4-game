"""Actual linked complete-extent yield, checked ordinary and ownership.

Independent endpoint checks bytes/CRC/credit. Prepared planner data is a
fixture here; actual producer ordering/timing is checked in both full replays.
"""
import argparse,json,struct
from pathlib import Path
from check_nes_supply723 import Row
from check_nes_rows713 import Peer
from check_nes_supply485_arm import crc
from check_nes_tail729 import spans,oam
from nes_raw506 import sha
from check_nes_dma637 import QuietProbe
from check_nes_game478 import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_PC,UC_ARM_REG_LR

class Prepared(QuietProbe):
 def hook(self,u,at,size,user):
  if at==self.syms.get('nes_plan200_progress') and u.reg_read(UC_ARM_REG_R1)==2:
   # Explicit checked-empty producer fixture. The real endpoint is used in
   # boundary() above, and the full replay supplies actual two-bank jobs.
   self.put(self.test_sink,'nes_native_sink165','map_pair683',1,1)
  if at==self.callback:
   b=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R2)))
   if len(self.heads)==self.reject_at:
    u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
   if b[0]!=3:self.u.mem_write(self.window+self.layout['nes_sink_window184']['last'],b[:10])
  super().hook(u,at,size,user)

def prepared(src,case):
 m=Prepared(src,'normal');m.heads=[];m.test_sink=sink=0x20015800;plan=0x20016300;m.window=window=0x20016b00
 m.samples=m.drains=0;m.reasons=[];m.stop_at=m.bad_drain=0;m.reject_final=case=='bad_final'
 m.reject_at={'partial_first':1,'partial_pair':2,'partial_ordinary':3}.get(case,-1)
 for k,v,n in [('serial',48,4),('generation',952,2),('displayed',1,1),('state',1,1),('plan',plan,4),('enqueue',m.callback|1,4),('exchange',m.callback|1,4),('ack635',0 if case=='cold' else 45|(46<<32),8)]:m.put(sink,'nes_native_sink165',k,v,n)
 for k,v,n in [('window',window,4),('guard',m.guard|1,4),('bank_history',0 if case=='cold' else 2,1)]:m.put(plan,'nes_plan200',k,v,n)
 mask=(1<<64)-1 if case=='cold' else 0xfff
 for k,v,n in [('prepared',case!='not_prepared',1),('open',1,1),('displayed',1,1),('serial',48,4),('generation',951 if case=='stale_generation' else 952,2),('target',1,1),('map_upload',mask,8)]:m.put(m.resident,'nes_resident211',k,v,n)
 for k,v,n in [('valid',1,1),('generation',952,2),('bg_count',1,2),('obj_count',16,2),('hdma_size',21,2),('display_mask',0x1e,1)]:m.put(m.video,'nes_native_video165',k,v,n)
 if case=='unowned_tile':m.u.mem_write(m.resident+m.layout['nes_resident211']['used'],b'\x01')
 data=bytes((i*37+i//13)&255 for i in range(4096));m.u.mem_write(m.video+m.layout['nes_native_video165']['map'],data)
 ok=m.call('nes_sink212_seal',[sink,m.video,m.resident,4192]);positive=case in ('normal','cold')
 assert bool(ok)==positive,(case,ok,len(m.heads))
 if case in ('not_prepared','stale_generation','unowned_tile'):assert not m.heads
 if positive:
  maps=[b for b in m.heads if b[1]==2];recovered={}
  for b in maps:
   off,n=struct.unpack('<HH',b[10:14]);assert b[0]==2 and b[16:]==data[off:off+n]
   for i,v in enumerate(b[16:],off):assert i not in recovered;recovered[i]=v
  assert len(recovered)==(4096 if case=='cold' else 768)
  if case=='normal':assert [b[1] for b in m.heads[:5]]==[2,2,2,2,4]
  assert m.before_final==(0 if case=='cold' else 45|(46<<32))
  assert m.get(sink,'nes_native_sink165','ack635',8)>>32==48
 else:assert m.get(sink,'nes_native_sink165','ack635',8)==45|(46<<32)
 m.call('nes_sink165_reset',[sink,m.callback|1,0]);assert not m.get(sink,'nes_native_sink165','ack635',8)
 return dict(case=case,passed=True,committed=bool(ok),order=[(b[0],b[1],int.from_bytes(b[10:12],'little')) for b in m.heads])

class Ordinary(Peer):
 def __init__(self):super().__init__('normal');self.order=[]
 def exchange(self,tx,clock):
  if tx[0]==0xe1:
   self.order.append((tx[1],tx[2],int.from_bytes(tx[11:13],'little')))
   if tx[2]==3:
    self.advance(clock);self.calls.append(tx.hex());b=tx[1:-2]
    assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
    assert b[0]==2 and b[16:]==bytes(range(16))
    assert int.from_bytes(b[2:4],'little')==self.sent and ((self.sent-self.retired)&65535)<4
    self.sent=(self.sent+1)&65535;self.pending.append((clock+200,b));return bytes(len(tx))
  return super().exchange(tx,clock)

def boundary(src,case):
 m=Row(src,'normal');e=m.endpoint=Ordinary();m.case='normal'
 for k,v,n in [('started',1,1),('ending',1,1),('generation',907,2),('bank_history',0 if case=='cold' else 2,1)]:m.put(m.p,'nes_plan200',k,v,n)
 m.put(m.s,'nes_native_sink165','plan',m.p,4)
 mask=(1<<64)-1 if case=='cold' else 0xfff
 if case=='sparse':mask=0x3f|(7<<9)
 if case=='short':mask=0x1f
 if case=='empty':mask=0
 if case=='tail':mask=1<<63
 if case=='ready_OBJ':e.jobs=[(1,1248,64,1)]
 if case in ('bad_E8_CRC','wrong_generation','ambiguous_E1'):e.mode=case
 if case=='wrong_generation':e.jobs=[(1,1248,64,1)]
 if case=='STOP':m.case='STOP'
 if case=='wrap':
  e.sent=e.retired=65534;m.put(m.w,'nes_sink_window184','sent',65534,2);m.put(m.w,'nes_sink_window184','retired',65534,2);m.put(m.s,'nes_native_sink165','sequence',65534,2)
 if case=='STOP_after_first':
  exchange=e.exchange
  def stop(tx,clock):
   r=exchange(tx,clock)
   if tx[0]==0xe1 and tx[2]==2:m.case='STOP'
   return r
  e.exchange=stop
 m.u.mem_write(m.video+m.layout['nes_native_video165']['map'],e.data)
 ok=m.call('map527',[m.s,m.video,mask&0xffffffff,mask>>32,4])
 # Packet sequence65535 is deliberately forbidden, unlike credit counters.
 # Preserve the exhaustion guard instead of wrapping an in-frame identity.
 positive=case not in ('wrap','STOP','STOP_after_first','bad_E8_CRC','wrong_generation','ambiguous_E1')
 assert bool(ok)==positive,(case,ok,e.order)
 first=list(e.maps)
 if case=='normal':assert first==[(i,192) for i in range(0,768,192)],(case,first)
 if case=='sparse':assert first==[(0,192),(192,192)],(case,first)
 if case in ('wrap','STOP_after_first'):assert first==[(0,192)],(case,first)
 if case=='ready_OBJ':assert first==[(i,192) for i in range(0,768,192)],(case,first)
 if case=='cold':assert sum(n for _,n in first)==4096
 if case=='short':assert first==[(0,192),(192,128)]
 if case=='tail':assert first==[(4032,64)]
 if positive:
  m.u.mem_write(m.q,bytes(range(16)))
  assert m.call('span',[m.s,3,0,m.q,16]),(case,e.order)
  assert m.call('map527',[m.s,m.video,mask&0xffffffff,mask>>32,0]),(case,e.order)
  seen=[i for off,n in e.maps for i in range(off,off+n)]
  expected=[i for row in range(64) if mask>>row&1 for i in range(row*64,row*64+64)]
  assert sorted(seen)==expected and len(seen)==len(set(seen)),(case,e.maps)
  assert sum(section==3 for op,section,off in e.order)==1
 else:
  before=len(e.calls);assert not m.call('map527',[m.s,m.video,mask&0xffffffff,mask>>32,4]);assert len(e.calls)==before
 assert not m.get(m.s,'nes_native_sink165','displayed')
 assert not m.call('nes_plan200_retire',[m.p]) and not e.rearmed
 m.call('nes_sink165_reset',[m.s,m.syms['nes_window184_barrier']|1,m.w])
 assert not m.get(m.s,'nes_native_sink165','map_next') and not m.get(m.s,'nes_native_sink165','ack635',8)
 return dict(case=case,passed=True,first_maps=first,maps=e.maps,order=e.order,final_ACK_not_granted=True,reset_invalidates=True)

def cursor(src,mask,start,mode):
 m=Row(src,'normal');e=m.endpoint=Ordinary();m.case='normal'
 for k,v,n in [('started',1,1),('ending',1,1),('generation',907,2),('bank_history',2,1)]:m.put(m.p,'nes_plan200',k,v,n)
 m.put(m.s,'nes_native_sink165','plan',m.p,4);m.put(m.s,'nes_native_sink165','map_next',start,1)
 m.u.mem_write(m.video+m.layout['nes_native_video165']['map'],e.data)
 assert m.call('map527',[m.s,m.video,mask&0xffffffff,mask>>32,mode])
 return dict(maps=e.maps,next=m.get(m.s,'nes_native_sink165','map_next'),grant=m.get(m.s,'nes_native_sink165','map_pair683'))

def run(a):
 if a.cursor_only:
  masks=(0,0xffffffffffffffff,0x3f,0x8000000000000000,0xffffff00000000,0x8000000180000001,0x5555555555555555,0x00000007003f0000)
  rows=[]
  for mask in masks:
   for mode in range(4):
    start=31 if mask==0x8000000180000001 else 0
    b=cursor(a.base,mask,start,mode);c=cursor(a.arm,mask,start,mode);assert b==c,(hex(mask),mode,b,c)
    rows.append(dict(mask=hex(mask),start=start,mode=mode,result=c))
  a.out.write_text(json.dumps(dict(stage=732,passed=True,scope='Actual linked old modes0..3, sparse/dense/bit63/zero/partial cursor; timings excluded.',base=sha(a.base/'obj-nes-100/firmware.stm'),firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows),indent=2)+'\n')
  print('PASS732:32 paired old-mode cursor cases');return
 cases=('normal','wrap','cold','sparse','short','empty','tail','ready_OBJ','STOP','STOP_after_first','bad_E8_CRC','wrong_generation','ambiguous_E1')
 r=dict(stage=732,passed=True,scope=__doc__,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),boundaries=[boundary(a.arm,c) for c in cases],prepared=[prepared(a.arm,c) for c in ('normal','cold','not_prepared','stale_generation','unowned_tile','partial_first','partial_pair','partial_ordinary','bad_final')],span=spans(a.base,a.arm),oam=oam(a.base,a.arm))
 a.out.write_text(json.dumps(r,indent=2)+'\n');print('PASS732:13 pair/ordinary/fault,9 prepared/partial/final,76 span,8 OAM')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--cursor-only',action='store_true')
 for n in ('base','arm','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
