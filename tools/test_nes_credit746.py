# SPDX-License-Identifier: MIT
"""Execute the real ARM memcpy at the final map's checked credit boundary."""
import sys
from pathlib import Path
from unittest.mock import patch

from check_nes_game478 import UC_ARM_REG_PC, UC_HOOK_CODE
from elftools.elf.elffile import ELFFile
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7
from test_nes_raw506_joint import Runtime
import test_nes_handoff745 as legacy
import test_nes_arm745 as joint


def observe(original, split):
    def init(cpu, args, link):
        original(cpu,args,link)
        with Path('../probes/nes-oam746/probe.elf').open('rb') as f:
            elf=ELFFile(f)
            code=elf.get_section_by_name('.text')
            entries={s.name:s['st_value'] for s in elf.get_section_by_name('.symtab').iter_symbols()}
            assert code['sh_addr']==0x0807fa00
            cpu.u.mem_write(code['sh_addr'],code.data())
        scratch=0x2001fe00
        window=cpu.rt+cpu.layout['nes_native_runtime165']['transport']
        ly=cpu.layout['nes_sink_window184']
        # Only redirect 957 after the baseline has actually issued its final map.
        # The linked C runs separately from boot and includes general admission cost.
        active=drain=False
        expected=b''
        dest=0
        def number(address,n):
            return int.from_bytes(cpu.u.mem_read(address,n),'little')
        def event(tag,done):
            cpu.events.append(dict(event='credit746',point=tag,done=done,generation=957,clock=cpu.clock,
                sent=number(window+ly['sent'],2),retired=number(window+ly['retired'],2)))
        def edge(u,pc,size,ctx):
            nonlocal active,drain,dest,expected
            if cpu.irq or cpu.generation!=957:return
            done=number(scratch+12,4)
            if pc==0x801e40e and not active:
                assert not expected
                dest=u.reg_read(UC_ARM_REG_R6)
                serial=number(u.reg_read(UC_ARM_REG_R5)+4*u.reg_read(UC_ARM_REG_R4),4)
                expected=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),112))+serial.to_bytes(4,'little')
                active=True
                entry='start746'
            elif not active:return
            elif pc==0x801f0f2:
                drain=True
                return
            elif pc==0x8021986 and drain and done<116:
                assert u.reg_read(UC_ARM_REG_R4)==window
                assert u.reg_read(UC_ARM_REG_R7)==number(window+ly['sent'],2)
                assert number(window+ly['last']+1,1)==2
                assert number(window+ly['retired'],2)!=number(window+ly['sent'],2)
                entry='piece746' if split else 'full746'
            elif pc==0x801f116 and drain:
                drain=False
                if done==116:return
                entry='fallback746'
            elif pc==0x801e42e:
                assert done==116 and bytes(u.mem_read(dest,116))==expected
                active=False
                event('checked',done)
                return
            else:return
            event(entry,done)
            u.reg_write(UC_ARM_REG_PC,entries[entry]|1)
        def write(u,access,address,size,value,context):
            if active and value:
                assert value in (56,116) and bytes(u.mem_read(dest,value))==expected[:value]
                event('written',value)
        for pc in (0x801e40e,0x801f0f2,0x8021986,0x801f116,0x801e42e):
            cpu.u.hook_add(UC_HOOK_CODE,edge,begin=pc,end=pc)
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,write,begin=scratch+12,end=scratch+15)
    return init


if __name__=='__main__':
    split='--split' in sys.argv
    if split:sys.argv.remove('--split')
    init=observe(legacy.controlled(Runtime.__init__,reserve=True),split)
    with patch.object(Runtime,'__init__',init),patch.object(joint,'instrument',legacy.arm_late(joint.instrument)):
        joint.run()
