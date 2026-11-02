# SPDX-License-Identifier: MIT
"""Isolate the extra E8 sample within exactly one terminal retry budget."""
import argparse
import json
from pathlib import Path
from check_nes_prelude554 import Pending,ARM,UC_HOOK_CODE,UC_ARM_REG_R0,UC_ARM_REG_LR,UC_ARM_REG_PC,crc,sha


class Second(Pending):
    def __init__(self,case):
        super().__init__();self.case=case;self.armed=False;self.samples=0

    def exchange(self,tx,clock):
        if self.armed and tx[0]==0xe8:
            self.samples+=1
            if self.samples==2:
                if self.case!='busy':self.held=False
                if self.case=='bulk':self.jobs=[(1,0,32,1)]
        result=bytearray(super().exchange(tx,clock))
        if tx[0]==0xe8 and self.armed and self.samples==2:
            if self.case=='count':result[5]^=1
            if self.case=='reserved':result[18]=1
            if self.case=='ended':result[3]=2
            result[19]=crc(result[1:19],8,7,0)^(self.case=='crc')
        return bytes(result)


def run(src,case,extra):
    m=ARM(src,'normal');ep=m.endpoint=Second(case);m.setup()
    marker=0x0807ff80
    def empty(u,pc,size,user):
        m.put(m.p,'nes_plan200','quiet_map',0,4)
        u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    m.u.hook_add(UC_HOOK_CODE,empty,begin=marker,end=marker)
    for key,val,size in [('started',1,1),('generation',907,2),('quiet_map',marker|1,4)]:
        m.put(m.p,'nes_plan200',key,val,size)
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    assert m.call('nes_plan200_end',[m.p]) and not ep.accepted
    m.put(m.p,'nes_plan200','poll_limit',1,4)
    start=len(ep.calls);ep.armed=True
    m.call('nes_plan200_progress',[m.p,1])
    ops=[int(s[:2],16) for s in ep.calls[start:]]
    assert ops[:2]==([0xe8,0xe8] if extra else [0xe8])
    if extra and case=='ready':
        assert ops[:3]==[0xe8,0xe8,0xe9] and ep.accepted==1
    else:
        assert not ep.accepted and 0xe9 not in ops
        if extra and case=='bulk':assert 0xe1 in ops
    assert not ep.rearmed and not m.get(m.s,'nes_native_sink165','displayed')
    return dict(case=case,samples=ep.samples,operations=ops)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('base','arm','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    rows=[run(a.base,'ready',False)]+[run(a.arm,k,True) for k in ('ready','busy','count','reserved','ended','crc','bulk')]
    a.out.write_text(json.dumps(dict(sha=sha(a.arm/'obj-nes-100/firmware.stm'),rows=rows),indent=2)+'\n')
