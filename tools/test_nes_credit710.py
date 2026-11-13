"""709 E1 model plus read-only actual ARM parser/snapshot observations."""
import runpy
from unittest.mock import patch
from test_nes_raw506_joint import Link,Runtime
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1
from test_nes_credit709 import response as shared_response

init=Runtime.__init__
def observe_init(self,*args,**kwargs):
    init(self,*args,**kwargs);self.link.observer710=self
    def checked(u,at,size,user):
        if self.irq:return
        w=u.reg_read(UC_ARM_REG_R0);rx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),20))
        self.events.append(dict(event='full_response710',generation=self.generation,clock=self.clock,
            retired_before=self.get(w,'nes_sink_window184','retired',2),reply=rx.hex()))
    at=self.syms['response709'];self.u.hook_add(UC_HOOK_CODE,checked,begin=at,end=at)

def response(self,tx):
    rx=shared_response(self,tx)
    if tx[0]==0xe1 and hasattr(self,'observer710'):
        m=self.observer710;w=m.rt+m.layout['nes_native_runtime165']['transport']
        m.events.append(dict(event='E1_snapshot710',generation=m.generation,clock=m.clock,length=len(tx),
            retired_before=m.get(w,'nes_sink_window184','retired',2),sent_before=m.get(w,'nes_sink_window184','sent',2),
            reply=rx[:20].hex()))
    return rx

if __name__=='__main__':
    with patch.object(Link,'response',response),patch.object(Runtime,'__init__',observe_init):
        runpy.run_module('test_nes_longrun694',run_name='__main__')
