"""Actual baseline/candidate slot state and emitted40B descriptors, including STOP."""
import argparse,json,struct
from pathlib import Path
from check_nes_game478 import Machine,sha
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR

class Probe(Machine):
 def hook(self,u,pc,size,user):
  if pc==getattr(self,'writer',0) and getattr(self,'stop',False):
   u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  super().hook(u,pc,size,user)

def run(a):
 pair=[Probe(p,bytes(128)) for p in (a.base,a.arm)];rows=[]
 for m in pair:m.plans=[]
 def same(label):
  b,c=pair
  assert b.plans==c.plans,label
  for name,addr in [('nes_native_video165','video'),('nes_resident211','resident')]:
   assert bytes(b.u.mem_read(getattr(b,addr),b.layout[name]['size']))==bytes(c.u.mem_read(getattr(c,addr),c.layout[name]['size'])),(label,name)
  rows.append(dict(case=label,passed=True,emits=len(c.plans)))
 def begin(epoch,gen):
  for m in pair:assert m.call('nes_resident211_begin',[m.resident,epoch,1,gen,m.writer|1,0])
 def slot(label,gen,tag,kind,mask,key,ready=False,shape=None,reject=False):
  result=[]
  for i,m in enumerate(pair):
   q=0x20012000
   rows0=bytes(16) if kind==2 else bytes(n//2 for n in range(16))
   canonical=shape or rows0+b'\xff'*16
   data=struct.pack('<HHHBB',gen,0,tag,kind,mask)+(bytes([0xa5])*32 if i and not ready else canonical)
   m.u.mem_write(q,data);args=[m.resident,m.video,key&0xffffffff,key>>32,q]
   if i:args.append(int(ready))
   result.append(m.call('nes_resident211_slot',args))
  assert result[0]==result[1] and (result[1]==65535)==reject,(label,result)
  same(label)
 begin(1,907)
 slot('zero',907,0,2,0,0,True)
 slot('cold_BG_miss',907,4,0,255,4|0x1fed6c8da4480000)
 slot('same_frame_BG_hit_poisoned_rows',907,4,0,255,4|0x1fed6c8da4480000)
 slot('OBJ_miss',907,8,1,3,8|(3<<13))
 slot('OBJ_hit_poisoned_rows',907,8,1,3,8|(3<<13))
 shape=bytes(reversed(bytes(n//2 for n in range(16))))+struct.pack('<8H',65535,7,*([65535]*6))
 slot('exceptional_BG_miss',907,4,0,255,(1<<63)|17,True,shape)
 slot('exceptional_BG_hit',907,4,0,255,(1<<63)|17,True,shape)
 slot('wrong_generation',908,9,0,255,9|0x1fed6c8da4480000,reject=True)
 slot('wrong_kind',907,9,3,255,9,True,reject=True)
 for m in pair:
  assert m.call('nes_resident211_prepare',[m.resident,0,0,0])
 slot('prepared_rejects',907,4,0,255,4|0x1fed6c8da4480000,reject=True)
 for m in pair:assert m.call('nes_resident211_commit',[m.resident,1,907,0,1])
 same('commit_bank0')
 begin(1,908);slot('bank1_retained_key_needs_write',908,4,0,255,4|0x1fed6c8da4480000)
 for m in pair:
  assert m.call('nes_resident211_prepare',[m.resident,0,0,0]);assert m.call('nes_resident211_commit',[m.resident,2,908,1,1])
 begin(1,909);slot('bank0_retained_content',909,4,0,255,4|0x1fed6c8da4480000)
 for m in pair:m.stop=True
 slot('STOP_during_new_BG_write',909,99,0,255,99|0x1fed6c8da4480000,reject=True)
 slot('fault_blocks_existing_hit',909,4,0,255,4|0x1fed6c8da4480000,reject=True)
 for m in pair:
  m.stop=False;assert not m.call('nes_resident211_begin',[m.resident,1,1,910,m.writer|1,0]);m.call('nes_resident211_reset',[m.resident])
 begin(2,910);slot('reset_epoch_cold_write',910,4,0,255,4|0x1fed6c8da4480000)
 same('STOP_invalidates_both_banks_cold_map')
 # Zero uses an all-zero shape, not the ordinary identity template. The
 # new internal deferred mode must reject it before touching ownership.
 m=Probe(a.arm,bytes(128));m.plans=[]
 assert m.call('nes_resident211_begin',[m.resident,1,1,907,m.writer|1,0])
 q=0x20012000;m.u.mem_write(q,struct.pack('<HHHBB',907,0,0,2,0)+bytes(16)+b'\xff'*16)
 before=bytes(m.u.mem_read(m.resident,m.layout['nes_resident211']['size']))
 assert m.call('nes_resident211_slot',[m.resident,m.video,0,0,q,0])==65535
 assert not m.plans and bytes(m.u.mem_read(m.resident,len(before)))==before
 rows.append(dict(case='deferred_zero_rejected_before_ownership_change',passed=True,emits=0))
 return dict(stage=716,passed=True,scope=__doc__+' Slot endpoint only; source/tag and physical schedules verified separately.',cases=rows,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),baseline=sha(a.base/'obj-nes-100/firmware.stm'))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','arm','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();r=run(a);a.out.write_text(json.dumps(r,indent=2)+'\n');print('PASS716 slot/descriptor/state guards',len(r['cases']))
