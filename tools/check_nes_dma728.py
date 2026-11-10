"""Linked OBJ handoff after real map E1/E0, with injected progress/clock edges.

Independent peer checks bytes/CRC/credit. Progress is injected as the existing
board ABI; no new RTL proof or real cycle timing is implied by these guards.
"""
import argparse,json
from pathlib import Path
from check_nes_supply723 import Row
from check_nes_rows713 import Peer
from check_nes_game478 import UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR
from check_nes_supply485_arm import crc
from nes_raw506 import sha

class Handoff(Row):
 def hook(self,u,at,size,user):
  if at==self.syms.get('nes_cost471_now'):
   u.reg_write(UC_ARM_REG_R0,getattr(self,'clock728',10000000)&0xffffffff)
   if not getattr(self,'frozen728',False):self.clock728=getattr(self,'clock728',10000000)+1000
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  if at==self.syms.get('nes_window184_drain'):
   if not getattr(self,'frozen728',False):self.clock728=getattr(self,'clock728',10000000)+8400
  super().hook(u,at,size,user)

def check(src,case):
 m=Handoff(src,'normal');e=m.endpoint=Peer('normal');m.clock728=10000000
 m.put(m.s,'nes_native_sink165','plan',m.p,4)
 for k,v in [('bank_history',2),('ending',1)]:m.put(m.p,'nes_plan200',k,v,1)
 m.u.mem_write(m.video+m.layout['nes_native_video165']['map'],e.data)
 assert m.call('map527',[m.s,m.video,7,0,1]) and e.maps==[(0,192)]
 m.put(m.w,'nes_sink_window184','wait',0x0807ff91,4)
 m.put(m.w,'nes_sink_window184','poll_limit',3 if case=='stopped_clock' else 65536,4)
 m.u.mem_write(m.data_symbols['nes_cost471_available'],(case!='no_clock').to_bytes(4,'little'))
 if case=='wrap':m.clock728=0xffffff00
 age=1397700-200000
 if case=='outside_window':age=504000
 if case=='stale':age=84000000
 m.put(m.s,'nes_native_sink165','ack_clock719',(m.clock728-age)&0xffffffff,4)
 m.frozen728=case=='stopped_clock'
 if case=='cold':m.put(m.p,'nes_plan200','bank_history',0,1)
 e.jobs=[(0 if case=='BG' else 1,0,16 if case=='BG' else 32,1)]
 old=e.exchange;counts={'map_E0':0,'map_before_OBJ':None}
 def exchange(tx,clock):
  r=old(tx,clock)
  if tx[0]==0xe0 and not e.bulk:
   counts['map_E0']+=1;b=bytearray(r)
   if case not in ('expiry','stopped_clock') and counts['map_E0']>=2 and b[2]==2:b[2]|=8
   if case=='bad_identity':b[10]^=1
   if case=='live_progress':b[2]|=9
   b[19]=crc(b[1:19],8,7,0)^(case=='bad_CRC')
   r=bytes(b)
   if case=='STOP_after_credit':m.case='STOP'
  if tx[0]==0xe1 and tx[1]==7:counts['map_before_OBJ']=counts['map_E0']
  return r
 e.exchange=exchange
 if case=='STOP':m.case='STOP'
 ok=m.call('nes_plan200_progress',[m.p,0])
 good=case not in ('STOP','STOP_after_credit','bad_identity','live_progress','bad_CRC')
 assert bool(ok)==good,(case,ok,e.calls[-3:])
 assert e.bulk==int(good) and not m.get(m.s,'nes_native_sink165','displayed')
 if good:
  assert m.get(m.p,'nes_plan200','bulk_pending') and counts['map_before_OBJ'] is not None
  if case in ('normal','wrap'):assert counts['map_before_OBJ']==2,counts
  if case=='BG':assert counts['map_before_OBJ']==1,counts
  if case in ('cold','outside_window','no_clock','stale'):assert counts['map_before_OBJ']==0,counts
  if case=='expiry':assert 2<counts['map_before_OBJ']<30,counts
  if case=='stopped_clock':assert counts['map_before_OBJ']==3,counts
 assert not m.call('nes_plan200_retire',[m.p]) and not e.rearmed
 return dict(case=case,passed=True,committed=False,bulk=e.bulk,**counts)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();cases=('normal','BG','cold','outside_window','no_clock','stale','wrap','expiry','stopped_clock','STOP','STOP_after_credit','bad_identity','live_progress','bad_CRC')
 r=dict(stage=728,passed=True,scope=__doc__,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=[check(a.arm,c) for c in cases])
 a.out.write_text(json.dumps(r,indent=2)+'\n');print('PASS728',len(cases),'actual map credit/OBJ ownership/expiry/STOP guards')
