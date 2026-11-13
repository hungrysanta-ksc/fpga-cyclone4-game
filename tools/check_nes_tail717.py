"""Actual linked poll path: retain map drain, remove only fill drain, no final ACK."""
import argparse,json
from pathlib import Path
from check_nes_supply485_arm import ARM,Endpoint,sha,UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR
from unicorn import UC_HOOK_CODE

class Probe(ARM):
 def __init__(self,src,case):
  super().__init__(src,'normal');self.case=case;self.drains=0
  if case in ('bad_E8_CRC','wrong_generation'):self.endpoint.mode=case
  def drain(*args):self.drains+=1
  self.u.hook_add(UC_HOOK_CODE,drain,begin=self.syms['nes_window184_drain'],end=self.syms['nes_window184_drain'])
 def hook(self,u,at,size,user):
  if at==0x0807ff90:
   u.reg_write(UC_ARM_REG_R0,int(self.case!='STOP'));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  if at==getattr(self,'guard485',0) and getattr(self,'case',None)=='STOP':
   u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  super().hook(u,at,size,user)

def check(src,new,kind,case):
 m=Probe(src,case);m.case='normal';m.setup();m.case=case;m.put(m.w,'nes_sink_window184','wait',0x0807ff91,4);e=m.endpoint;e.jobs=[(1,0,32,0)]
 for k,v,n in [('started',1,1),('ending',1,1),('generation',907,2),('bank_history',2,1)]:m.put(m.p,'nes_plan200',k,v,n)
 m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],bytes([5 if kind=='fill' else 2 if kind=='map' else 7,5 if kind=='fill' else 2 if kind=='map' else 1])+bytes(8))
 ok=m.call('nes_plan200_progress',[m.p,0]);positive=case=='normal'
 assert bool(ok)==positive,(kind,case,ok,m.get(m.p,'nes_plan200','error'),m.get(m.w,'nes_sink_window184','error'),m.get(m.s,'nes_native_sink165','error'),e.calls[-4:])
 if positive:
  assert m.drains==int(kind=='map' or (kind=='fill' and not new)),(kind,m.drains)
  assert e.bulk==1 and m.get(m.p,'nes_plan200','bulk_pending') and not e.retired
 else:assert not e.bulk
 assert not m.get(m.s,'nes_native_sink165','displayed')
 assert not m.call('nes_plan200_retire',[m.p]) and not e.rearmed
 return dict(kind=kind,case=case,drains=m.drains,bulk=e.bulk,actual_receipt_still_owed=positive,final_ACK_required=True)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','arm','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();r={}
 for name,src,new in [('base',a.base,False),('candidate',a.arm,True)]:
  r[name]=dict(firmware=sha(src/'obj-nes-100/firmware.stm'),cases=[check(src,new,k,c) for k in ('map','fill','tile') for c in ('normal','STOP','bad_E8_CRC','wrong_generation')])
 a.out.write_text(json.dumps(dict(passed=True,scope=__doc__+' Last-head, empty window and bounded-input callback are injected; endpoint gives a delayed real bulk receipt, no hardware timing.',variants=r),indent=2)+'\n')
 print('PASS717 24 paired drain/identity/STOP/final-ACK cases')
