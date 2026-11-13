"""Actual715 ARM: initialized scratch, BG-before-map, row immutability checks."""
import runpy,hashlib
from unittest.mock import patch
from test_nes_raw506_joint import Runtime
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP

def observe(original):
 def init(cpu,args,link):
  original(cpu,args,link);L=cpu.layout
  at=cpu.video+L['nes_native_video165']['map'];scratch=cpu.video+L['nes_native_video165']['oam']
  active=0;generation=None;initialized=set();writes=[set() for _ in range(32)];issued={}
  def record(event,**kw):cpu.events.append(dict(event=event,generation=cpu.generation,clock=cpu.clock,**kw))
  def start(u,pc,size,user):
   nonlocal active,generation,initialized,writes,issued
   if cpu.irq:return
   generation=cpu.generation;active=0;initialized=set();writes=[set() for _ in range(32)];issued={}
  def emit(u,pc,size,user):
   nonlocal active
   if cpu.irq or generation!=cpu.generation:return
   q=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),40))
   if q[6]==2:assert active==0;active=1
  def memory(u,access,address,size,value,user):
   if generation!=cpu.generation or not active:return
   if address>=scratch:
    for pos in range(address,min(address+size,scratch+2144)):
     if access==17: # Unicorn UC_MEM_WRITE; read callback is16
      if active==1:initialized.add(pos-scratch)
      else:raise AssertionError(('715 scratch write after BG reservation',generation,pos-scratch))
     else:assert pos-scratch in initialized,('715 uninitialized scratch read',generation,pos-scratch)
    return
   if access!=17:return
   assert active==2,('715 map materialized before BG fence',generation)
   raw=value.to_bytes(size,'little')
   for pos in range(max(at,address),min(at+4096,address+size)):
    i=pos-at;writes[(i//64)%32].add(i)
    if i in issued:assert raw[pos-address]==issued[i],('715 changed issued map',generation,i)
  def offer(u,pc,size,user):
   nonlocal active
   if cpu.irq:return
   phase=u.reg_read(UC_ARM_REG_R1);groups=u.mem_read(cpu.video+L['nes_native_video165']['groups'],1)[0]
   if phase==0:
    assert active==1
    refs=bytes(u.mem_read(scratch+2112,groups))
    for g,ref in enumerate(refs):
     assert ref<=g and refs[ref]==ref and 2112+g in initialized
     assert all(ref*66+i in initialized for i in range(66))
     vals=bytes(u.mem_read(scratch+ref*66,66));assert all(int.from_bytes(vals[i:i+2],'little')<1024 for i in range(0,66,2))
    active=2;record('BG_reserved715',groups=groups,unique_rows=len(set(refs)),scratch_written=len(initialized))
   else:assert active==2
   record('offer715',phase=phase,completed_rows=sum(len(x)==66 for x in writes))
  def clear(u,pc,size,user):
   nonlocal active
   if cpu.irq or active!=2:return
   if u.reg_read(UC_ARM_REG_R0)==scratch and u.reg_read(UC_ARM_REG_R2)==544:
    groups=u.mem_read(cpu.video+L['nes_native_video165']['groups'],1)[0]
    assert all(len(writes[g])==66 for g in range(groups))
    record('map_complete715',groups=groups,SHA256=hashlib.sha256(bytes(u.mem_read(at,4096))).hexdigest());active=0
  def packet(u,pc,size,user):
   if cpu.irq or generation!=cpu.generation:return
   op,sec,off=(u.reg_read(r) for r in (UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3))
   if sec!=2 or op not in (2,24):return
   sp=u.reg_read(UC_ARM_REG_SP);ptr,n=(int.from_bytes(u.mem_read(sp+i,4),'little') for i in (0,4))
   assert ptr==at+off and off%64==n%64==0 and 0<n<=192
   groups=u.mem_read(cpu.video+L['nes_native_video165']['groups'],1)[0]
   for row in range(off//64,(off+n)//64):assert row%32>=groups or len(writes[row%32])==66
   data=bytes(u.mem_read(ptr,n));assert all(off+i not in issued for i in range(n));issued.update((off+i,b) for i,b in enumerate(data))
   record('map715',offset=off,bytes=n,op=op)
  for name,fn in [('nes_native_video211_plan',start),('nes_plan200_emit',emit),('offer527',offer),('memset',clear),('packet_wire',packet)]:
   pc=cpu.syms[name];cpu.u.hook_add(UC_HOOK_CODE,fn,begin=pc,end=pc)
  cpu.u.hook_add(UC_HOOK_MEM_WRITE,memory,begin=at,end=at+4095)
  cpu.u.hook_add(UC_HOOK_MEM_WRITE|UC_HOOK_MEM_READ,memory,begin=scratch,end=scratch+2143)
 return init

if __name__=='__main__':
 with patch.object(Runtime,'__init__',observe(Runtime.__init__)):
  runpy.run_module('test_nes_longrun694',run_name='__main__')
