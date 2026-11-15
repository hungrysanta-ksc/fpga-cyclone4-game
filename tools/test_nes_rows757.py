# SPDX-License-Identifier: MIT
"""Observe destination map stores and first current-generation slot ownership on linked ARM."""
import runpy
from unittest.mock import patch
from test_nes_raw506_joint import Runtime
from unicorn import UC_HOOK_MEM_WRITE


def observe(original, generation=957, low=2048, high=3583):
    def init(cpu, args, link):
        original(cpu,args,link)
        start=cpu.video+cpu.layout['nes_native_video165']['map']
        used=cpu.resident+cpu.layout['nes_resident211']['used']
        def store(u,access,address,size,value,user):
            if cpu.generation!=generation:return
            old=bytes(u.mem_read(address,size))
            new=(value% (1<<(size*8))).to_bytes(size,'little')
            cpu.events.append(dict(event='map_store757',generation=generation,clock=cpu.clock,
                                   offset=address-start,old=old.hex(),new=new.hex()))
        def mark(u,access,address,size,value,user):
            if cpu.generation!=generation:return
            cpu.events.append(dict(event='slot_used757',generation=generation,clock=cpu.clock,
                                   byte=address-used,size=size,value=value% (1<<(size*8))))
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,store,begin=start+low,end=start+high)
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,mark,begin=used,end=used+127)
    return init


if __name__=='__main__':
    with patch.object(Runtime,'__init__',observe(Runtime.__init__)):
        runpy.run_module('test_nes_window756',run_name='__main__')
