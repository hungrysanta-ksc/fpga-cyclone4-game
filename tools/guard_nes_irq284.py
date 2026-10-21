# SPDX-License-Identifier: MIT
"""Actual ARM PB8 routing, WFI, exception-frame, W1C and unrelated-wake checks."""
import argparse,json,shutil
from pathlib import Path
from nes_delta231 import sha
from probe_nes_refill284 import ARM
from unicorn.arm_const import UC_ARM_REG_PRIMASK


class Endpoint:
    def __init__(self):self.exception_cycles=0;self.now=0;self.waits=0;self.level=1
    def wait(self):
        self.waits+=1;self.now+=1000;self.arm.gpio(self.level)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);shutil.copyfile(a.source/'output.elf',d/'output.elf')
    ep=Endpoint();arm=ARM(d/'output.elf',ep);ep.arm=arm;uc=arm.uc;cases=[]
    def word(a):return int.from_bytes(uc.mem_read(a,4),'little')
    arm.call('irq_init284',[])
    assert not arm.enabled()
    arm.call('irq_begin284',[])
    assert arm.enabled() and word(0x40020400)&(3<<16)==0
    assert word(0x40013c0c)&256==0
    cases.append('PB8/SYSCFG/EXTI8/rising/NVIC23 configured by actual ARM')
    # Pending before foreground entry: real ISR runs first, high level avoids WFI.
    arm.gpio(1);arm.call('wait284',[]);assert ep.waits==0 and len(arm.exti)==1
    assert word(arm.symbols['wakes284'])==1 and not arm.pending
    cases.append('edge before wait, handler W1C, no lost level')
    # WFI observes pending even while PRIMASK masks exception delivery.
    for i in range(32):
        arm.gpio(0);ep.level=1;before=len(arm.exti);waits=ep.waits
        arm.call('wait284',[])
        assert ep.waits==waits+1 and len(arm.exti)==before+1 and not uc.reg_read(UC_ARM_REG_PRIMASK)
        assert arm.exti[-1]['frame'][7]&0x1ff==0
    cases.append('32 masked-WFI arrivals, real handler, eight-word frame restored')
    # A timer/unrelated wake may cause checked fallback; cannot create a receipt.
    arm.gpio(0);ep.level=0;before=len(arm.exti);arm.call('wait284',[])
    assert len(arm.exti)==before and not arm.pending
    cases.append('unrelated wake returns without false EXTI')
    # EXTI9_5 handler owns only line8 and leaves another line pending.
    arm.pr=1<<7;arm.pending=False;arm.call('EXTI9_5_IRQHandler',[]);assert arm.pr==1<<7
    cases.append('unowned EXTI bit retained')
    arm.call('irq_end284',[]);assert not arm.enabled();before=len(arm.exti)
    for _ in range(32):arm.gpio(0);arm.gpio(1);arm.call('reset259',[])
    assert len(arm.exti)==before
    cases.append('source phase PB8 changes masked, no IRQ service')
    arm.call('irq_begin284',[]);assert arm.enabled() and not arm.pending
    cases.append('new checked output ownership discards old pending edge')
    uc.mem_write(arm.symbols['plan_error267'],(1).to_bytes(4,'little'))
    assert arm.call('finish267',[])==0 and not arm.enabled()
    cases.append('failed plan finish releases EXTI ownership')
    assert all(r['entry_exit_cycles']==24 and r['instructions']>0 for r in arm.exti)
    result=dict(passed=True,cases=cases,EXTI=arm.exti,MMIO=arm.mmio,ELF_sha256=sha(d/'output.elf'),
        script_sha256=sha(Path(__file__)),entry_exit='24 allocated zero-wait cycles, not hardware WCET',physical=False,full_RUN=False)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,cases=len(cases),exceptions=len(arm.exti))))


if __name__=='__main__':main()
