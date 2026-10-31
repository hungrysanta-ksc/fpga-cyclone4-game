# SPDX-License-Identifier: MIT
"""Observe unchanged506 M4 function intervals and modeled ROM slots, without retiming."""
import argparse,json
from pathlib import Path
import test_nes_raw506_joint as joint
from check_nes_game478 import sha
from unicorn.arm_const import UC_ARM_REG_LR,UC_ARM_REG_SP

class TraceLink(joint.Link):
    def __init__(self,a):
        self.rom_trace=[];super().__init__(a)
    def next_rom(self,t):
        done=super().next_rom(t)
        self.rom_trace.append(dict(generation=self.generation,requested=t,completed=done))
        return done

class TraceRuntime(joint.Runtime):
    last=None
    def __init__(self,a,link):
        self.intervals=[];self.trace_stack=[];self.trace_symbols=None
        super().__init__(a,link);TraceRuntime.last=self
    def hook(self,u,at,size,user):
        if self.live and not self.irq and self.clock<self.next_irq:
            if self.trace_symbols is None:
                names=['nes_native_video211_plan','nes_plan200_finish','nes_sink212_seal']
                self.trace_symbols={self.syms[n]&~1:n for n in names}
            sp=u.reg_read(UC_ARM_REG_SP)
            if self.trace_stack and at==self.trace_stack[-1]['return_PC'] and sp==self.trace_stack[-1]['SP']:
                x=self.trace_stack.pop();x['end']=self.clock;self.intervals.append(x)
            if at in self.trace_symbols:
                self.trace_stack.append(dict(generation=self.generation,name=self.trace_symbols[at],start=self.clock,return_PC=u.reg_read(UC_ARM_REG_LR)&~1,SP=sp))
        return super().hook(u,at,size,user)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','data','fixture','plans','client','mesen','out','reference','driver503']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve()
    a.candidate=True;a.frames=12;a.cpi=2;a.capture_gate=True;a.spi_us=0;a.rom_stride=48;a.rom_phase=0;a.start=3000000
    joint.Link=TraceLink;joint.Runtime=TraceRuntime;joint.run(a)
    m=TraceRuntime.last;assert not m.trace_stack and len(m.intervals)==36
    old=json.loads((a.reference/'joint.json').read_text());new=json.loads((a.out/'joint.json').read_text())
    for key in ['firmware_SHA256','client_SHA256','parameters','frames','ARM_instructions','SysTick_calls','SysTick_instructions','wire_B','ROM_read_allocations','vram_DMA_B']:
        assert old[key]==new[key],key
    for g in range(905,917):assert sha(a.reference/f'frame-{g}.rgb')==sha(a.out/f'frame-{g}.rgb')
    r=dict(passed=True,unchanged_schedule=True,intervals=m.intervals,ROM_model_slots=m.link.rom_trace,scope=__doc__,reference_joint_SHA256=sha(a.reference/'joint.json'),firmware_SHA256=new['firmware_SHA256'])
    (a.out/'trace507.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
    print('PASS507 observation: exact instruction/IRQ/wire/ACK/RGB equivalence,36 function intervals')
