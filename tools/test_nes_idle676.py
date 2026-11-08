"""Observe bounded map-idle input work without changing emulated instructions or time."""
import runpy
from unittest.mock import patch
from test_nes_raw506_joint import Runtime
from check_nes_game478 import UC_HOOK_CODE,UC_ARM_REG_R0,UC_ARM_REG_R2,UC_ARM_REG_LR,UC_ARM_REG_SP

def observe(original):
    def init(cpu,args,link):
        original(cpu,args,link)
        pending={};hooks=set();layout=cpu.layout
        def fields():
            def get(addr,kind,name,n=1):return int.from_bytes(cpu.u.mem_read(addr+layout[kind][name],n),'little')
            rt=cpu.rt;receiver=get(rt,'nes_native_runtime165','receiver',4)
            transport=rt+layout['nes_native_runtime165']['transport']
            return dict(receiver_state=get(receiver,'nes_native165','state'),input_generation=get(receiver,'nes_native165','generation',2),
                next_token=get(receiver,'nes_native165','next_token',2),prefetch_left=get(rt,'nes_native_runtime165','prefetch_left'),
                sent=get(transport,'nes_sink_window184','sent',2),retired=get(transport,'nes_sink_window184','retired',2))
        def returned(u,pc,size,user):
            key=(pc,u.reg_read(UC_ARM_REG_SP))
            if key not in pending:return
            begin=pending.pop(key)
            cpu.events.append(dict(event='idle676_return',generation=cpu.generation,clock=cpu.clock,begin=begin,
                passed=u.reg_read(UC_ARM_REG_R0),**fields()))
        def entered(u,pc,size,user):
            if cpu.irq or u.reg_read(UC_ARM_REG_R2)!=4:return
            f=fields();assert f['sent']==f['retired'],'not an empty output queue'
            cpu.events.append(dict(event='idle676_enter',generation=cpu.generation,clock=cpu.clock,**f))
            ret=u.reg_read(UC_ARM_REG_LR)&~1;pending[(ret,u.reg_read(UC_ARM_REG_SP))]=cpu.clock
            if ret not in hooks:hooks.add(ret);u.hook_add(UC_HOOK_CODE,returned,begin=ret,end=ret)
        pc=cpu.syms['wait634'];cpu.u.hook_add(UC_HOOK_CODE,entered,begin=pc,end=pc)
    return init

if __name__=='__main__':
    with patch.object(Runtime,'__init__',observe(Runtime.__init__)):
        runpy.run_module('test_nes_ready673',run_name='__main__')
