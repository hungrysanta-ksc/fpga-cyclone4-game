"""Observe final-ACK and map-idle checked input credit without changing target instructions or modeled time."""
import runpy
from hashlib import sha256
from unittest.mock import patch
from test_nes_raw506_joint import Runtime
from check_nes_game478 import UC_HOOK_CODE,UC_ARM_REG_R0,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_LR,UC_ARM_REG_SP

def observe(original):
    def init(cpu,args,link):
        original(cpu,args,link)
        cpu.events.append(dict(event='image682_start',generation=cpu.generation,clock=cpu.clock,firmware=sha256((args.arm/'obj-nes-100/firmware.stm').read_bytes()).hexdigest()))
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
            cpu.events.append(dict(event='input682_return',generation=cpu.generation,clock=cpu.clock,begin=begin,
                passed=u.reg_read(UC_ARM_REG_R0),**fields()))
        def entered(u,pc,size,user):
            if cpu.irq or u.reg_read(UC_ARM_REG_R2) not in (0,1,2,4):return
            f=fields();f.update(reason=u.reg_read(UC_ARM_REG_R2),progress=u.reg_read(UC_ARM_REG_R3))
            cpu.events.append(dict(event='input682_enter',generation=cpu.generation,clock=cpu.clock,**f))
            ret=u.reg_read(UC_ARM_REG_LR)&~1;pending[(ret,u.reg_read(UC_ARM_REG_SP))]=dict(clock=cpu.clock,**f)
            if ret not in hooks:hooks.add(ret);u.hook_add(UC_HOOK_CODE,returned,begin=ret,end=ret)
        pc=cpu.syms['wait634'];cpu.u.hook_add(UC_HOOK_CODE,entered,begin=pc,end=pc)
        poll_pending={};poll_hooks=set()
        def poll_returned(u,pc,size,user):
            key=(pc,u.reg_read(UC_ARM_REG_SP))
            if key not in poll_pending:return
            begin=poll_pending.pop(key)
            cpu.events.append(dict(event='input682_poll_return',generation=cpu.generation,clock=cpu.clock,begin=begin,
                passed=u.reg_read(UC_ARM_REG_R0),**fields()))
        def poll_entered(u,pc,size,user):
            if cpu.irq:return
            ret=u.reg_read(UC_ARM_REG_LR)&~1
            poll_pending[(ret,u.reg_read(UC_ARM_REG_SP))]=dict(clock=cpu.clock,**fields())
            if ret not in poll_hooks:poll_hooks.add(ret);u.hook_add(UC_HOOK_CODE,poll_returned,begin=ret,end=ret)
        pc=cpu.syms['nes_native165_poll'];cpu.u.hook_add(UC_HOOK_CODE,poll_entered,begin=pc,end=pc)

    return init

if __name__=='__main__':
    with patch.object(Runtime,'__init__',observe(Runtime.__init__)):
        runpy.run_module('test_nes_progress680',run_name='__main__')
