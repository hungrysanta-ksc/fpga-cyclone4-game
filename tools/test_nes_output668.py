"""Read-only span-search timing on the actual ARM/65816/ROM replay."""
import runpy
from unittest.mock import patch
from check_nes_game478 import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_R0, UC_ARM_REG_R1
from test_nes_raw506_joint import Runtime


def profile(original):
    def init(cpu,args,link):
        original(cpu,args,link)
        pending={}; returns=set()
        def returned(u,pc,size,user):
            if cpu.irq:return
            key=(pc,u.reg_read(UC_ARM_REG_SP))
            if key not in pending:return
            clock,instructions,g,n=pending.pop(key)
            cpu.events.append(dict(event='scan668',generation=g,clock=cpu.clock,
                                   start=clock,instructions=cpu.instructions-instructions,
                                   length=n,result=u.reg_read(UC_ARM_REG_R0)))
        def entered(u,pc,size,user):
            if cpu.irq:return
            ret=u.reg_read(UC_ARM_REG_LR)&~1
            key=(ret,u.reg_read(UC_ARM_REG_SP))
            assert key not in pending
            pending[key]=(cpu.clock,cpu.instructions,cpu.generation,u.reg_read(UC_ARM_REG_R1))
            if ret not in returns:
                returns.add(ret);u.hook_add(UC_HOOK_CODE,returned,begin=ret,end=ret)
        pc=cpu.syms['span_piece']
        cpu.u.hook_add(UC_HOOK_CODE,entered,begin=pc,end=pc)
    return init


if __name__=='__main__':
    with patch.object(Runtime,'__init__',profile(Runtime.__init__)):
        runpy.run_module('test_nes_output664',run_name='__main__')
