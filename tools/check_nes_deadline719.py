"""Execute719 linked seal with clock/transport endpoints, not cycle timing.

Check skip, expiry, STOP, final ACK timestamp ownership, cold and DWT wrap.
Actual two-phase replay remains necessary for deadline and throughput claims.
"""
import argparse,json
from pathlib import Path
from check_nes_dma637 import QuietProbe
from check_nes_game478 import UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR
from nes_raw506 import sha

class Deadline(QuietProbe):
 def hook(self,u,at,size,user):
  if at==self.syms.get('nes_cost471_now'):
   u.reg_write(UC_ARM_REG_R0,getattr(self,'frozen719',self.clock719)&0xffffffff)
   self.clock719+=1000
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  if at in (self.guard,self.syms.get('nes_window184_drain')):
   self.clock719+=8400
  if at==self.syms.get('nes_window184_drain'):
   if self.event719 and self.drains==2:self.put(self.window719,'nes_sink_window184','status_flags',10,1)
  super().hook(u,at,size,user)

def check(src,case,*,map_input=None):
 m=Deadline(src,'normal');m.clock719=10000000;m.event719=case not in ('expiry','stopped_clock')
 if case=='wrap':m.clock719=0xffffff00
 m.heads=[];m.test_sink=sink=0x20015800;plan=0x20016300;window=m.window719=0x20016b00
 age=1397700+504000 if case=='current_deadline' else 2795400-200000
 if case=='budget_boundary':age=1397700-672000
 if case=='budget_after':age=1397700-672000+1
 if case=='stopped_clock':m.frozen719=m.clock719
 if case=='stale':age=84000000
 stamp=(m.clock719-age)&0xffffffff
 m.samples=m.drains=0;m.reasons=[];m.stop_at=1 if case=='STOP' else 0
 m.bad_drain=1 if case=='bad_credit' else 0;m.reject_final=case=='bad_final'
 m.u.mem_write(m.data_symbols['nes_cost471_available'],(case!='no_clock').to_bytes(4,'little'))
 for k,v,n in [('serial',48,4),('generation',952,2),('displayed',1,1),('state',1,1),('plan',plan,4),
  ('enqueue',m.callback|1,4),('exchange',m.callback|1,4),('ack635',45|(46<<32),8),('ack_clock719',stamp,4)]:m.put(sink,'nes_native_sink165',k,v,n)
 for k,v,n in [('window',window,4),('guard',m.guard|1,4),('bank_history',0 if case=='cold' else 2,1)]:m.put(plan,'nes_plan200',k,v,n)
 m.put(window,'nes_sink_window184','wait',0 if case=='no_callback' else m.guard|1,4)
 m.put(window,'nes_sink_window184','poll_limit',2 if case in ('poll_bound','stopped_clock') else 65536,4)
 m.put(window,'nes_sink_window184','status_flags',10 if case=='DMA_done' else 2,1)
 m.u.mem_write(window+m.layout['nes_sink_window184']['last'],bytes([7,1] if case=='last_tile' else [2,2])+bytes(8))
 for k,v,n in [('prepared',1,1),('open',1,1),('displayed',1,1),('serial',48,4),('generation',952,2),('target',1,1)]:m.put(m.resident,'nes_resident211',k,v,n)
 for k,v,n in [('valid',1,1),('generation',952,2),('bg_count',1,2),('obj_count',16,2),('hdma_size',21,2),('display_mask',0x1e,1)]:m.put(m.video,'nes_native_video165',k,v,n)
 if map_input:
  policy,kind,size=map_input
  m.u.mem_write(m.data_symbols['nes_cost471_available'],bytes(4))
  for k in ('ending','bulk_valid'):m.put(plan,'nes_plan200',k,1,1)
  if policy=='repay':m.put(plan,'nes_plan200','bg_input_due',1,1)
  m.u.mem_write(plan+m.layout['nes_plan200']['bulk'],bytes((1,kind))+size.to_bytes(2,'little')+bytes(8))
 ok=m.call('nes_sink212_seal',[sink,m.video,m.resident,4192]);positive=case not in ('STOP','bad_credit','bad_final')
 assert bool(ok)==positive,(case,ok,m.drains,m.samples)
 if map_input:
  applies=policy=='repay' or (kind==1 and size>=256)
  assert m.drains==int(applies) and m.samples==int(applies and case!='bad_credit')
  assert m.reasons==[4]*m.samples
  assert m.get(sink,'nes_native_sink165','ack635',8)==45|((48 if ok else 46)<<32)
  return dict(policy=policy,kind=kind,size=size,case=case,committed=bool(ok),drains=m.drains,input=m.samples)
 if case in ('cold','last_tile','no_clock','stale','current_deadline','budget_boundary'):assert m.drains==m.samples==0,case
 if case in ('normal','wrap','bad_final','budget_after'):assert (m.drains,m.samples)==(3,2),(case,m.drains,m.samples)
 if case=='expiry':assert 2<m.samples<20,(case,m.samples)
 if case in ('poll_bound','stopped_clock'):assert (m.drains,m.samples)==(2,2)
 if case=='DMA_done':assert (m.drains,m.samples)==(1,0)
 assert m.reasons==[4]*m.samples
 assert m.get(sink,'nes_native_sink165','ack635',8)==45|((48 if ok else 46)<<32)
 new_stamp=m.get(sink,'nes_native_sink165','ack_clock719',4)
 assert (new_stamp!=stamp)==bool(ok),(case,stamp,new_stamp)
 m.call('nes_sink165_reset',[sink,m.callback|1,0])
 assert m.get(sink,'nes_native_sink165','ack_clock719',4)==0
 assert m.get(sink,'nes_native_sink165','ack635',8)==0
 return dict(case=case,committed=bool(ok),drains=m.drains,callbacks=m.samples,checked_final_ACK_owns_timestamp=True,common_reset_invalidates=True)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();cases=('normal','current_deadline','budget_boundary','budget_after','DMA_done','expiry','poll_bound','stopped_clock','cold','last_tile','no_clock','stale','wrap','STOP','bad_credit','bad_final','no_callback')
 r=dict(passed=True,scope=__doc__,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=[check(a.arm,c) for c in cases])
 a.out.write_text(json.dumps(r,indent=2)+'\n');print('PASS719',len(cases),'linked admission/expiry/STOP/ACK boundaries')
