"""Linked713 frontier, credit, CRC, STOP, reset and final-ACK separation."""
import argparse,json,struct
from pathlib import Path
from check_nes_supply485_arm import ARM,Endpoint,crc,sha

class Peer(Endpoint):
 def __init__(self,mode):super().__init__(mode);self.maps=[];self.data=bytes((i*37+i//13)&255 for i in range(4096))
 def advance(self,clock):
  while self.pending and self.pending[0][0]<=clock:
   _,b=self.pending.pop(0)
   if b[0]==7:
    self.stale=self.descriptor();self.stale_reads=2;self.jobs.pop(0)
   self.retired=(self.retired+1)&65535;self.last=bytes((0,b[0]))+b[2:10]+b'\x65\x9a'
 def exchange(self,tx,clock):
  if tx[0]==0xe1 and tx[1] in (2,4):
   self.advance(clock);self.calls.append(tx.hex());b=tx[1:-2]
   assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big') and b[1]==2
   assert int.from_bytes(b[2:4],'little')==self.sent and ((self.sent-self.retired)&65535)<4
   off,n=struct.unpack('<HH',b[10:14]);assert b[0]==2 and b[16:]==self.data[off:off+n]
   self.maps.append((off,n));self.sent=(self.sent+1)&65535;self.pending.append((clock+200,b));return bytes(len(tx))
  r=super().exchange(tx,clock)
  if tx[0]==0xe0 and self.mode=='bad_credit':r=r[:-1]+bytes((r[-1]^1,))
  return r

def exercise(src,mode):
 m=ARM(src,mode);m.endpoint=Peer(mode);m.setup();e=m.endpoint;e.calls=[]
 m.put(m.s,'nes_native_sink165','plan',m.p,4)
 for k,v,n in [('started',1,1),('generation',907,2),('bank_history',2,1)]:m.put(m.p,'nes_plan200',k,v,n)
 mask=sum(1<<i for i in (*range(6),*range(32,38)))
 if mode=='last_rows':mask=(1<<31)|(1<<63)
 if mode=='cold':mask=(1<<64)-1
 if mode=='empty':mask=0
 m.u.mem_write(m.video+m.layout['nes_native_video165']['map'],e.data)
 m.put(m.s,'nes_native_sink165','map_ready',32 if mode in ('last_rows','cold') else 3,1)
 if mode=='three_credits':
  m.put(m.w,'nes_sink_window184','sent',1,2);m.put(m.w,'nes_sink_window184','retired',65534,2)
 if mode=='STOP':e.mode='STOP_after_E9';e.accepted=1
 if mode=='ready_tile':e.jobs=[(0,0,16,1)]
 def call():return bool(m.call('map527',[m.s,m.video,mask&0xffffffff,mask>>32,3]))
 ok=call();assert ok==(mode not in ('STOP','bad_E8_CRC','ambiguous_E1')),(mode,ok)
 if mode=='cold':
  m.put(m.p,'nes_plan200','ending',1,1);m.put(m.p,'nes_plan200','finished',1,1)
  assert m.call('map527',[m.s,m.video,mask&0xffffffff,mask>>32,0])
  seen=[i for off,n in e.maps for i in range(off,off+n)]
  assert sorted(seen)==list(range(4096)) and len(set(seen))==4096
 if mode in ('normal','last_rows'):
  assert call()
  assert e.maps==([(0,192),(2048,192)] if mode=='normal' else [(1984,64),(4032,64)])
  before=len(e.calls);assert call() and before==len(e.calls)
  if mode=='normal':
   for ready in (5,6):
    assert m.call('nes_window184_through',[m.w,m.q+300,e.sent])
    m.put(m.s,'nes_native_sink165','map_ready',ready,1);assert call() and call()
   assert e.maps==[(0,192),(2048,192),(192,128),(2240,128),(320,64),(2368,64)]
  assert not m.get(m.s,'nes_native_sink165','displayed') and not e.rearmed
  assert not m.call('nes_plan200_retire',[m.p]) and not e.rearmed
 elif mode in ('empty','three_credits','STOP','bad_E8_CRC','ready_tile'):assert not e.maps
 if mode=='ready_tile':assert e.bulk==1 and m.get(m.p,'nes_plan200','bulk_pending')
 if not ok:
  before=len(e.calls);assert not call() and len(e.calls)==before
 # Common reset clears both frontiers and all committed display history.
 m.call('nes_sink165_reset',[m.s,m.syms['nes_window184_barrier']|1,m.w])
 assert all(m.get(m.s,'nes_native_sink165',n)==0 for n in ('map_next','map_other','map_ready','map_page','displayed'))
 return dict(case=mode,passed=True,maps=e.maps,operations=[int(x[:2],16) for x in e.calls])

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();rows=[exercise(a.arm,n) for n in ('normal','last_rows','cold','empty','three_credits','ready_tile','STOP','bad_E8_CRC','ambiguous_E1')]
 a.out.write_text(json.dumps(dict(stage=713,passed=True,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows,scope=__doc__),indent=2)+'\n');print('PASS713',len(rows),'linked frontier/owner guards')
