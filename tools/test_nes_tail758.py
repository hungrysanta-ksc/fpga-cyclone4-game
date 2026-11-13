# SPDX-License-Identifier: MIT
"""Time resident slot and map-word functions without charging target instructions."""
import runpy
from unittest.mock import patch
from test_nes_raw506_joint import Runtime
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_SP


def observe(original):
    def init(cpu,args,link):
        original(cpu,args,link)
        active={}
        returns=set()
        def finish(u,pc,size,user):
            key=(pc,u.reg_read(UC_ARM_REG_SP))
            if key in active:
                name,start=active.pop(key)
                cpu.events.append(dict(event='work758',generation=957,name=name,start=start,clock=cpu.clock))
        def begin(u,pc,size,name):
            if cpu.generation!=957 or cpu.irq:return
            target=u.reg_read(UC_ARM_REG_LR)&~1
            key=(target,u.reg_read(UC_ARM_REG_SP))
            assert key not in active
            active[key]=(name,cpu.clock)
            if target not in returns:
                returns.add(target)
                u.hook_add(UC_HOOK_CODE,finish,begin=target,end=target)
        for name in ('nes_resident211_slot','map_word185'):
            if name not in cpu.syms:continue  # The halfword writer can be inlined.
            addr=cpu.syms[name]
            cpu.u.hook_add(UC_HOOK_CODE,begin,name,begin=addr,end=addr)
    return init


if __name__=='__main__':
    with patch.object(Runtime,'__init__',observe(Runtime.__init__)):
        runpy.run_module('test_nes_rows757',run_name='__main__')
