"""Bind a read-only owner observer to Runtime, including runpy entry points."""
import runpy
from unittest.mock import patch
from test_nes_raw506_joint import Runtime
from check_nes_game478 import UC_HOOK_CODE,UC_ARM_REG_R1,UC_ARM_REG_LR,UC_ARM_REG_SP,UC_ARM_REG_R0

def observe(original):
    def init(cpu,args,link):
        original(cpu,args,link)
        plan=cpu.rt+cpu.layout['nes_native_runtime165']['plan']
        sink=cpu.rt+cpu.layout['nes_native_runtime165']['sink'];pending={};hooks=set();bound=False
        def fields():
            def get(at,kind,key,n=1):return int.from_bytes(cpu.u.mem_read(at+cpu.layout[kind][key],n),'little')
            return dict(grant=get(sink,'nes_native_sink165','map_pair683'),
                bulk_pending=get(plan,'nes_plan200','bulk_pending'),bulk_valid=get(plan,'nes_plan200','bulk_valid'),
                bulk_until=get(plan,'nes_plan200','bulk_until',2),finished=get(plan,'nes_plan200','finished'))
        def returned(u,pc,size,user):
            key=(pc,u.reg_read(UC_ARM_REG_SP))
            if cpu.irq or key not in pending:return
            begin=pending.pop(key)
            cpu.events.append(dict(event='owner688_return',generation=cpu.generation,clock=cpu.clock,
                begin=begin,result=u.reg_read(UC_ARM_REG_R0),**fields()))
        def entered(u,pc,size,user):
            nonlocal bound
            if cpu.irq or u.reg_read(UC_ARM_REG_R1)!=2:return
            if not bound:print('OWNER688 bound to linked map progress',flush=True);bound=True
            if cpu.generation not in (905,951,952,954,955,956,957):return
            ret=u.reg_read(UC_ARM_REG_LR)&~1;pending[(ret,u.reg_read(UC_ARM_REG_SP))]=dict(clock=cpu.clock,**fields())
            if ret not in hooks:hooks.add(ret);u.hook_add(UC_HOOK_CODE,returned,begin=ret,end=ret)
        pc=cpu.syms['nes_plan200_progress'];cpu.u.hook_add(UC_HOOK_CODE,entered,begin=pc,end=pc)
    return init

if __name__=='__main__':
    with patch.object(Runtime,'__init__',observe(Runtime.__init__)):
        runpy.run_module('test_nes_seal686',run_name='__main__')
