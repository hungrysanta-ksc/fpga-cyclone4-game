"""Observe the actual BG-complete callback; no target time or schedule changes."""
import runpy
from hashlib import sha256
from unittest.mock import patch
from test_nes_raw506_joint import Runtime
from test_nes_receive682 import observe as receive
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_LR,UC_ARM_REG_SP

def observe(original):
    def init(cpu,args,link):
        original(cpu,args,link)
        layout=cpu.layout;pending={};hooks=set();last_write={}
        def get(addr,kind,name,n=1):return int.from_bytes(cpu.u.mem_read(addr+layout[kind][name],n),'little')
        video=get(cpu.rt,'nes_native_runtime165','video',4)
        at=video+layout['nes_native_video165']['map'];sink=cpu.rt+layout['nes_native_runtime165']['sink']
        def wrote(u,access,address,size,value,user):
            for g in range((address-at)//64,(address+size-1-at)//64+1):last_write[g]=cpu.clock
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,wrote,begin=at,end=at+4095)
        def fields():
            return dict(map_next=get(sink,'nes_native_sink165','map_next'),pair=get(sink,'nes_native_sink165','map_pair683'),
                map_sha=sha256(bytes(cpu.u.mem_read(at,4096))).hexdigest(),last_map_write=max(last_write.values(),default=0))
        def returned(u,pc,size,user):
            key=(pc,u.reg_read(UC_ARM_REG_SP))
            if key not in pending:return
            begin=pending.pop(key)
            cpu.events.append(dict(event='bg684_return',generation=cpu.generation,clock=cpu.clock,begin=begin,passed=u.reg_read(UC_ARM_REG_R0),**fields()))
        def entered(u,pc,size,user):
            if cpu.irq:return
            begin=dict(clock=cpu.clock,final=u.reg_read(UC_ARM_REG_R1),**fields())
            cpu.events.append(dict(event='bg684_enter',generation=cpu.generation,**begin))
            ret=u.reg_read(UC_ARM_REG_LR)&~1;pending[(ret,u.reg_read(UC_ARM_REG_SP))]=begin
            if ret not in hooks:hooks.add(ret);u.hook_add(UC_HOOK_CODE,returned,begin=ret,end=ret)
        pc=cpu.syms['offer527'];cpu.u.hook_add(UC_HOOK_CODE,entered,begin=pc,end=pc)
    return init

if __name__=='__main__':
    with patch.object(Runtime,'__init__',observe(receive(Runtime.__init__))):
        runpy.run_module('test_nes_progress680',run_name='__main__')
