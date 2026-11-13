# SPDX-License-Identifier: MIT
"""Observe real OAM stack writes, their credit state, and the final checked identity."""
from unittest.mock import patch
from check_nes_game478 import UC_HOOK_CODE, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2
from unicorn import UC_HOOK_MEM_WRITE
from test_nes_raw506_joint import Runtime
import test_nes_arm745 as joint


def observe(original):
    def init(cpu,args,link):
        original(cpu,args,link)
        layout=cpu.layout['nes_sink_window184']
        window=cpu.rt+cpu.layout['nes_native_runtime165']['transport']
        field=window+layout['pending_oam']
        hooks={}
        active=0
        source=serial=0
        edges=[]
        written=set()
        def number(address,n):return int.from_bytes(cpu.u.mem_read(address,n),'little')
        def watch(u,access,address,size,value,context):
            if not active:return
            lo=max(0,address-active);hi=min(116,address+size-active)
            if lo>=hi:return
            retired=number(window+layout['retired'],2)
            sent=number(window+layout['sent'],2)
            if not edges or edges[-1]['retired']!=retired or edges[-1]['sent']!=sent:
                edges.append(dict(retired=retired,sent=sent,first=cpu.clock,count=0))
            edges[-1].update(last=cpu.clock,count=edges[-1]['count']+hi-lo)
            written.update(range(lo,hi))
        def published(u,access,address,size,value,context):
            nonlocal active,edges,written
            if not active and not value:return
            if value:
                assert not active and size==4
                active=value;edges=[];written=set()
                if value not in hooks:hooks[value]=u.hook_add(UC_HOOK_MEM_WRITE,watch,begin=value,end=value+115)
            else:
                assert written==set(range(116))
                assert bytes(u.mem_read(active,116))==bytes(u.mem_read(source,112))+serial.to_bytes(4,'little')
                cpu.events.append(dict(event='OAM746',generation=cpu.generation,clock=cpu.clock,
                                       stack_address=active,serial=serial,segments=edges))
                active=0
        def send(u,pc,size,context):
            nonlocal source,serial
            source=u.reg_read(UC_ARM_REG_R1)+cpu.layout['nes_native_video165']['oam']
            serial=number(u.reg_read(UC_ARM_REG_R0)+cpu.layout['nes_native_sink165']['ack635']+4*u.reg_read(UC_ARM_REG_R2),4)
        cpu.u.hook_add(UC_HOOK_CODE,send,begin=cpu.syms['send635'],end=cpu.syms['send635'])
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,published,begin=field,end=field+3)
    return init


if __name__=='__main__':
    with patch.object(Runtime,'__init__',observe(Runtime.__init__)):
        joint.run()
