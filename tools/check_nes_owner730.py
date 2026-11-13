"""Linked seal ordering/failure/deadline plus unchanged real plan safeguards.

The seal test intercepts the progress endpoint to inject service delay/fault;
real E8/receipt/STOP semantics are exercised separately by gate721/owner676.
No synthetic endpoint timing is used as a throughput result.
"""
import argparse,json
from pathlib import Path
from unittest.mock import patch
import check_nes_deadline719 as old
from check_nes_game478 import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_PC,UC_ARM_REG_LR
from check_nes_tail729 import spans,oam
from nes_raw506 import sha
from check_nes_supply485_arm import ARM,Endpoint

def chain(src,case):
 m=ARM(src,'normal');m.setup();e=m.endpoint
 for k,v,n in [('started',1,1),('ending',1,1),('generation',907,2)]:m.put(m.p,'nes_plan200',k,v,n)
 e.jobs=[] if case=='empty' else [(1,1248,64,1),(1,1344,64,2)]
 e.end=case=='ended';released=False;advance=e.advance
 def release(clock):
  nonlocal released
  advance(clock)
  if e.retired and not released:
   e.jobs.append((1,1632,256,3));released=True
  assert len(e.jobs)<=2
 e.advance=release
 if case in ('STOP_after_bulk','wrong_generation','bad_E8_CRC','bad_ACK','ambiguous_E1'):e.mode=case
 ok=m.call('nes_plan200_progress',[m.p,3])
 positive=case in ('normal','empty','ended');assert bool(ok)==positive,(case,ok)
 if positive:
  assert e.bulk==e.retired==(0 if case=='empty' else 3)
  assert not m.get(m.p,'nes_plan200','bulk_pending') and not e.jobs
  assert bool(m.get(m.p,'nes_plan200','finished'))==(case=='ended')
 assert not m.get(m.s,'nes_native_sink165','displayed')
 assert not m.call('nes_plan200_retire',[m.p]) and not e.rearmed
 return dict(case=case,passed=True,bulk=e.bulk,retired=e.retired,final_display_ACK=False)

class Boundary(old.Deadline):
 instances=[]
 delay=0
 reject=False
 def __init__(self,*args):
  super().__init__(*args);self.order=[];self.instances.append(self)
 def hook(self,u,at,size,user):
  if at==self.syms.get('nes_plan200_progress'):
   self.order.append(('progress',u.reg_read(UC_ARM_REG_R1),self.clock719))
   if len(self.order)==1:
    self.clock719+=self.delay
    if self.reject:
     u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  if at==self.syms.get('nes_window184_drain'):self.order.append(('drain',self.clock719))
  super().hook(u,at,size,user)

def run(a):
 expected_mode=3 if a.ready_chain else 0
 cases=('normal','current_deadline','budget_boundary','budget_after','DMA_done','expiry','poll_bound','stopped_clock','cold','last_tile','no_clock','stale','wrap','STOP','bad_credit','bad_final','no_callback')
 rows=[]
 with patch.object(old,'Deadline',Boundary):
  for case in cases:
   r=old.check(a.arm,case);m=Boundary.instances[-1]
   if m.drains:
    assert m.order[0][0:2]==('progress',expected_mode),(case,m.order)
    before=m.order[:next(i for i,x in enumerate(m.order) if x[0]=='drain')]
    assert len(before)==1,(case,before)
   r['first_service_before_wait']=bool(m.drains);rows.append(r)
 # Reuse full seal setup but independently check injected outcomes. The old
 # helper expects ordinary admission counts, so only its final expectations
 # are adapted; all target setup and final history assertions stay identical.
 import inspect
 source=inspect.getsource(old.check)
 source=source.replace("positive=case not in ('STOP','bad_credit','bad_final')","positive=not Boundary.reject")
 lo=source.index(" if case in ('cold'");hi=source.index(' assert m.reasons==',lo)
 source=source[:lo]+source[hi:]
 env=dict(old.__dict__,Deadline=Boundary,Boundary=Boundary);exec(source,env)
 extra=[]
 for reject,delay in ((True,0),(False,250000)):
  Boundary.reject=reject;Boundary.delay=delay
  r=env['check'](a.arm,'normal');m=Boundary.instances[-1]
  assert m.drains==0 and m.samples==0,(reject,delay,m.order)
  assert m.order[0][:2]==('progress',expected_mode)
  assert any(h[0]==3 for h in m.heads)==(not reject)
  extra.append(dict(reject_service=reject,service_DWT_cycles=delay,deadline_not_restarted=True,no_early_history=reject,passed=True))
 Boundary.reject=False;Boundary.delay=0
 result=dict(stage=730,ready_chain=a.ready_chain,passed=True,scope=__doc__,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),deadline=rows,service=extra,span=spans(a.base,a.arm),oam=oam(a.base,a.arm))
 if a.ready_chain:result['chain']=[chain(a.arm,c) for c in ('normal','empty','ended','STOP_after_bulk','wrong_generation','bad_E8_CRC','bad_ACK','ambiguous_E1')]
 a.out.write_text(json.dumps(result,indent=2)+'\n');print('PASS730:17 deadline,2 service-fault/expiry,76 span,8 OAM')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--ready-chain',action='store_true')
 for n in ('base','arm','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
