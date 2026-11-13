"""Actual713 ARM/707D/unchanged65816 schedule with immutable row checks."""
import runpy,hashlib
from unittest.mock import patch
from test_nes_raw506_joint import Runtime
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP

def observe(original):
 def init(cpu,args,link):
  original(cpu,args,link)
  L=cpu.layout;sink=cpu.rt+L['nes_native_runtime165']['sink'];at=cpu.video+L['nes_native_video165']['map']
  generation=None;issued={};last_ready=0
  def get(k):return cpu.u.mem_read(sink+L['nes_native_sink165'][k],1)[0]
  def record(event,**kw):cpu.events.append(dict(event=event,generation=cpu.generation,clock=cpu.clock,**kw))
  def begin(u,pc,size,user):
   nonlocal generation,issued,last_ready
   if cpu.irq:return
   generation=cpu.generation;issued={};last_ready=0
  def write(u,access,address,size,value,user):
   if generation!=cpu.generation:return
   raw=value.to_bytes(size,'little')
   for pos in range(max(at,address),min(at+4096,address+size)):
    if pos-at in issued:assert raw[pos-address]==issued[pos-at],('713 map changed after issue',generation,pos-at)
  def offer(u,pc,size,user):
   nonlocal last_ready
   if cpu.irq:return
   rows=u.reg_read(UC_ARM_REG_R1);assert last_ready<=rows<=32
   last_ready=rows;record('ready713',rows=rows,left=get('map_next'),right=get('map_other'))
  def packet(u,pc,size,user):
   if cpu.irq or generation!=cpu.generation:return
   op,sec,off=(u.reg_read(r) for r in (UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3))
   if sec!=2 or op not in (2,24):return
   sp=u.reg_read(UC_ARM_REG_SP);p,n=(int.from_bytes(u.mem_read(sp+i,4),'little') for i in (0,4))
   ready=get('map_ready');assert p==at+off and off%64==n%64==0 and 0<n<=192
   assert off//2048==(off+n-1)//2048 and (off%2048+n)//64<=ready,(generation,off,n,ready)
   data=bytes(u.mem_read(p,n));assert all(off+i not in issued for i in range(n)),('duplicate713',generation,off)
   issued.update((off+i,b) for i,b in enumerate(data))
   record('map713',offset=off,bytes=n,ready=ready,op=op,SHA256=hashlib.sha256(data).hexdigest())
  for name,fn in [('nes_native_video211_plan',begin),('offer527',offer),('packet_wire',packet)]:
   pc=cpu.syms[name];cpu.u.hook_add(UC_HOOK_CODE,fn,begin=pc,end=pc)
  cpu.u.hook_add(UC_HOOK_MEM_WRITE,write,begin=at,end=at+4095)
 return init

if __name__=='__main__':
 with patch.object(Runtime,'__init__',observe(Runtime.__init__)):
  runpy.run_module('test_nes_longrun694',run_name='__main__')
