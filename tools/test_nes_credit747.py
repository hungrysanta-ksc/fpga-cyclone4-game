# SPDX-License-Identifier: MIT
"""Time two bounded E0 retry policies with 727's exact issue prefix and live replies."""
import argparse
import sys
from pathlib import Path
from unittest.mock import patch

from check_nes_game478 import UC_ARM_REG_PC, UC_HOOK_CODE
from elftools.elf.elffile import ELFFile
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R4, UC_ARM_REG_SP, UC_ARM_REG_R10
from test_nes_raw506_joint import Runtime
import test_nes_credit746 as previous
import test_nes_handoff745 as legacy
import test_nes_arm745 as joint


def retry(original,policy):
    def init(cpu,args,link):
        original(cpu,args,link)
        with Path('../probes/nes-credit747/probe.elf').open('rb') as f:
            elf=ELFFile(f)
            code=elf.get_section_by_name('.text')
            labels={s.name:s['st_value'] for s in elf.get_section_by_name('.symtab').iter_symbols()}
            cpu.u.mem_write(code['sh_addr'],code.data())
        if policy=='debt':
            with Path('../probes/nes-credit747/debt.elf').open('rb') as f:
                elf=ELFFile(f);code=elf.get_section_by_name('.text')
                cpu.u.mem_write(code['sh_addr'],code.data())
                labels.update({s.name:s['st_value'] for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name in ('hold747','pay747')})
        active=watch=owed=False
        def edge(u,pc,size,ctx):
            nonlocal active,watch,owed
            if cpu.irq or cpu.generation!=957:return
            if pc==0x801f0f2:
                # The ready OBJ follows the last map; the normal pre-drain
                # E8 checks and the separate previous BG receipt already ran.
                d=bytes(u.mem_read(u.reg_read(UC_ARM_REG_SP)+18,12))
                active=d[:4]==bytes((1,1,32,1))
            elif policy=='debt' and active and pc==0x801f108:
                owed=True
                cpu.events.append(dict(event='hold_input747',generation=957,clock=cpu.clock))
                u.reg_write(UC_ARM_REG_PC,labels['hold747']|1)
            elif policy=='debt' and owed and pc==0x801e42e:
                owed=False
                cpu.events.append(dict(event='repay_input747',generation=957,clock=cpu.clock))
                u.reg_write(UC_ARM_REG_PC,labels['pay747']|1)
            elif pc==0x801f116:
                active=watch=False
            elif active:
                if pc==cpu.syms['nes_wire723_crc8'] and policy in ('fold','debt'):
                    # Equal raw watermarks select a faster full CRC only.
                    # The original counter, signature and identity checks still run.
                    addr=u.reg_read(UC_ARM_REG_R0)
                    raw=bytes(u.mem_read(addr,18))
                    if u.reg_read(UC_ARM_REG_R1)!=18 or raw[0]!=0xf7 or raw[2:4]!=raw[4:6]:return
                    target='final_crc747'
                    cpu.events.append(dict(event='E0_fold747',generation=957,clock=cpu.clock))
                elif pc==0x802190a:
                    watch=False
                    cpu.events.append(dict(event='E0_enter747',generation=957,clock=cpu.clock))
                    if policy=='eager':return
                    target='begin747'
                elif pc==0x801987a:
                    assert u.reg_read(UC_ARM_REG_R4)==1
                    watch=True
                    target='eager747' if policy=='eager' else 'measured747'
                elif pc==0x801988e and watch:
                    target='compare747'
                elif pc==0x8019894 and watch:
                    cpu.events.append(dict(event='E0_quiet747',generation=957,clock=cpu.clock,
                                           budget=u.reg_read(UC_ARM_REG_R10)))
                    watch=False
                    return
                else:return
                u.reg_write(UC_ARM_REG_PC,labels[target]|1)
        for pc in (0x801f0f2,0x801f116,0x802190a,0x801987a,0x801988e,0x8019894,0x801f108,0x801e42e,cpu.syms['nes_wire723_crc8']):
            cpu.u.hook_add(UC_HOOK_CODE,edge,begin=pc,end=pc)
    return init


if __name__=='__main__':
    p=argparse.ArgumentParser(add_help=False)
    p.add_argument('--policy',choices=('measured','eager','fold','debt'),required=True)
    a,rest=p.parse_known_args()
    sys.argv=sys.argv[:1]+rest
    init=retry(previous.observe(legacy.controlled(Runtime.__init__,reserve=True),False),a.policy)
    with patch.object(Runtime,'__init__',init),patch.object(joint,'instrument',legacy.arm_late(joint.instrument)):
        joint.run()
