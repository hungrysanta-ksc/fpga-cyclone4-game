"""Observe716 exact hits and initialization before every deferred-shape read."""
import runpy
from unittest.mock import patch
from test_nes_raw506_joint import Runtime
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE,UC_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_SP,UC_ARM_REG_LR

def observe(original):
 def init(cpu,args,link):
  original(cpu,args,link);active=None;watched=set();returns=set();stats={}
  def memory(u,access,address,size,value,user):
   if cpu.irq or active is None or active['ready']:return
   lo,hi=active['q']+8,active['q']+40
   for p in range(max(address,lo),min(address+size,hi)):
    if access==UC_MEM_WRITE:active['initialized'].add(p)
    else:assert p in active['initialized'],('716 deferred shape read before initialized',cpu.generation,p-lo)
  def entered(u,pc,size,user):
   nonlocal active
   if cpu.irq:return
   assert active is None
   sp=u.reg_read(UC_ARM_REG_SP);q=int.from_bytes(u.mem_read(sp,4),'little');ready=int.from_bytes(u.mem_read(sp+4,4),'little')
   assert ready in (0,1)
   kind=u.mem_read(q+6,1)[0];assert kind<=2 and (ready or kind<2)
   active=dict(q=q,ready=ready,kind=kind,sp=sp,ret=u.reg_read(UC_ARM_REG_LR)&~1,initialized=set(),instructions=cpu.instructions)
   if q not in watched:
    watched.add(q);u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,memory,begin=q+8,end=q+39)
   if active['ret'] not in returns:
    returns.add(active['ret']);u.hook_add(UC_HOOK_CODE,returned,begin=active['ret'],end=active['ret'])
  def returned(u,pc,size,user):
   nonlocal active
   if cpu.irq or active is None or pc!=active['ret'] or u.reg_read(UC_ARM_REG_SP)!=active['sp']:return
   assert u.reg_read(UC_ARM_REG_R0)<(128 if active['kind']==1 else 1024)
   n=len(active['initialized']);assert active['ready'] or n in (0,32)
   name=('ready' if active['ready'] else 'hit' if not n else 'miss')+str(active['kind'])
   r=stats.setdefault(name,dict(calls=0,instructions=0));r['calls']+=1;r['instructions']+=cpu.instructions-active['instructions'];active=None
  def start(u,pc,size,user):
   nonlocal stats
   if not cpu.irq:assert active is None;stats={}
  def finish(u,pc,size,user):
   if cpu.irq:return
   assert active is None
   cpu.events.append(dict(event='slots716',generation=cpu.generation,clock=cpu.clock,stats={k:dict(v) for k,v in stats.items()}))
  for name,fn in [('nes_native_video211_plan',start),('nes_resident211_slot',entered),('nes_resident211_prepare',finish)]:
   pc=cpu.syms[name];cpu.u.hook_add(UC_HOOK_CODE,fn,begin=pc,end=pc)
 return init

if __name__=='__main__':
 with patch.object(Runtime,'__init__',observe(Runtime.__init__)):
  runpy.run_module('test_nes_longrun694',run_name='__main__')
