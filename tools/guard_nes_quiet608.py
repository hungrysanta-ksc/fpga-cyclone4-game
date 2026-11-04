"""Inject STOP inside either terminal pause and corrupt the first resumed status."""
import argparse
import json
from pathlib import Path

from check_nes_game478 import crc
from check_nes_supply485_arm import ARM, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_LR, sha


class QuietARM(ARM):
    def hook(self,u,at,size,user):
        if getattr(self,'testing',False):
            if at==self.syms['nes_cost474_pause']:
                self.pauses+=1
                self.guard_calls=0
            if at==self.guard485 and self.pauses:
                self.guard_calls+=1
                if self.pauses==self.stop and self.guard_calls==2:
                    u.reg_write(UC_ARM_REG_R0,0)
                    u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
                    return
        super().hook(u,at,size,user)


def check(src,stop,damage,expected):
    arm=QuietARM(src,'normal');arm.setup()
    for key,n,value in [('started',1,1),('ending',1,1),('generation',2,907)]:
        arm.put(arm.p,'nes_plan200',key,value,n)
    ops=[]
    def exchange(tx,clock):
        assert tx[0]==0xe8
        ops.append(clock)
        reply=bytearray(20);reply[1:4]=bytes([0xd7,4,0 if len(ops)==1 else 2])
        reply[-1]=crc(reply[1:19],8,7,0)^(damage and len(ops)==2)
        return bytes(reply)
    arm.endpoint.exchange=exchange
    arm.pauses=arm.guard_calls=0;arm.stop=stop;arm.testing=True
    ok=bool(arm.call('nes_plan200_progress',[arm.p,1]))
    assert ok==(not stop and not damage)
    assert len(ops)==(1 if stop else 2) and arm.pauses==(stop or expected)
    assert bool(arm.get(arm.p,'nes_plan200','finished'))==ok
    assert not arm.get(arm.s,'nes_native_sink165','displayed')
    if ok:
        assert not arm.call('nes_plan200_retire',[arm.p])
    return dict(stop_pause=stop,corrupt=damage,success=ok,polls=len(ops),pauses=arm.pauses)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','arm','report'):
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    results={}
    for src,n in [(a.base,1),(a.arm,2)]:
        results[sha(src/'obj-nes-100/firmware.stm')]=[
            check(src,stop,damage,n) for stop,damage in [(0,False),(0,True),*((i,False) for i in range(1,n+1))]]
    a.report.write_text(json.dumps(results,indent=2)+'\n')
