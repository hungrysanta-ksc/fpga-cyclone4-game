"""Actual linked ARM/unchanged65816: final BG fence, immutable map and grants."""
import runpy,hashlib
from unittest.mock import patch
from test_nes_raw506_joint import Runtime
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_LR,UC_ARM_REG_SP

def observe(original):
 def init(cpu,args,link):
  original(cpu,args,link)
  L=cpu.layout;at=cpu.video+L['nes_native_video165']['map']
  plan=cpu.rt+L['nes_native_runtime165']['plan'];sink=cpu.rt+L['nes_native_runtime165']['sink']
  current=None;frozen=None;issued={};pending={};returns=set();serial=0
  def get(p,t,k,n=1):return int.from_bytes(cpu.u.mem_read(p+L[t][k],n),'little')
  def state():
   return dict(sent=get(plan,'nes_plan200','sent',2),count=get(plan,'nes_plan200','count'),
    plan_bytes=get(plan,'nes_plan200','bytes',2),bulk_pending=get(plan,'nes_plan200','bulk_pending'),
    cursor=get(sink,'nes_native_sink165','map_next'))
  def record(event,**kw):cpu.events.append(dict(event=event,generation=cpu.generation,clock=cpu.clock,**kw))
  def start(u,pc,size,user):
   nonlocal current,frozen,issued
   if cpu.irq:return
   current=cpu.generation;frozen=None;issued={}
  def writes(u,access,address,size,value,user):
   if current!=cpu.generation or frozen is None:return
   raw=value.to_bytes(size,'little')
   for p in range(max(at,address),min(at+4096,address+size)):
    assert raw[p-address]==frozen[p-at],('714 changed immutable map',current,p-at)
  def done(u,pc,size,user):
   if cpu.irq:return
   for e in pending.pop((pc,u.reg_read(UC_ARM_REG_SP)),[]):
    record('return714',call=e['call'],name=e['name'],start=e['clock'],result=u.reg_read(UC_ARM_REG_R0),**state())
  def enter(name):
   def fn(u,pc,size,user):
    nonlocal frozen,serial
    if cpu.irq or current!=cpu.generation:return
    if name=='offer527':
     assert frozen is None
     frozen=bytes(u.mem_read(at,4096));record('frozen714',SHA256=hashlib.sha256(frozen).hexdigest(),**state())
    serial+=1;e=dict(call=serial,name=name,clock=cpu.clock)
    record('call714',call=serial,name=name,**state())
    ret=u.reg_read(UC_ARM_REG_LR)&~1;pending.setdefault((ret,u.reg_read(UC_ARM_REG_SP)),[]).append(e)
    if ret not in returns:returns.add(ret);u.hook_add(UC_HOOK_CODE,done,begin=ret,end=ret)
   return fn
  def packet(u,pc,size,user):
   if cpu.irq or current!=cpu.generation:return
   op,sec,off=(u.reg_read(r) for r in (UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3))
   if sec!=2 or op not in (2,24):return
   assert frozen is not None,('714 map before BG fence',current)
   sp=u.reg_read(UC_ARM_REG_SP);p,n=(int.from_bytes(u.mem_read(sp+i,4),'little') for i in (0,4))
   assert p==at+off and off%64==n%64==0 and 0<n<=192
   raw=bytes(u.mem_read(p,n));assert raw==frozen[off:off+n]
   assert all(off+i not in issued for i in range(n));issued.update((off+i,b) for i,b in enumerate(raw))
   record('map714',offset=off,bytes=n,op=op,**state())
  for name,fn in [('nes_native_video211_plan',start),('packet_wire',packet)]+[(n,enter(n)) for n in ('offer527','quiet528')]:
   pc=cpu.syms[name];cpu.u.hook_add(UC_HOOK_CODE,fn,begin=pc,end=pc)
  cpu.u.hook_add(UC_HOOK_MEM_WRITE,writes,begin=at,end=at+4095)
 return init

if __name__=='__main__':
 with patch.object(Runtime,'__init__',observe(Runtime.__init__)):
  runpy.run_module('test_nes_longrun694',run_name='__main__')
