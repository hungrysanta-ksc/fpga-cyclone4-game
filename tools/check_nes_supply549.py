# SPDX-License-Identifier: MIT
"""Exercise the new first-BG buffer, its row boundary and STOP in the linked ARM."""
import argparse
import json
from pathlib import Path
from check_nes_supply485_arm import ARM,sha,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_R0
from test_nes_bulk497_arm import Endpoint
from check_nes_order520 import record
from test_nes_raw506_joint import wire_plan


class StopARM(ARM):
    stopped=False
    def hook(self,u,at,size,user):
        if self.stopped and at==self.guard485:
            u.reg_write(UC_ARM_REG_R0,0)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            return
        return super().hook(u,at,size,user)


def run(src,warm,number,stop):
    arm=StopARM(src,'normal')
    arm.endpoint=Endpoint()
    arm.setup()
    arm.put(arm.p,'nes_plan200','defer_first',int(warm),1)
    assert arm.emit(2,0,0)
    for slot in range(1,number+1):
        assert arm.emit(0,slot,slot+20)
    def sizes():
        return [bytes.fromhex(tx)[3] for tx in arm.endpoint.calls if tx.startswith('e9')]
    before=sizes()
    assert before==([2] if not warm else [4] if number==3 else [])
    if warm and number<3:
        arm.stopped=stop
        assert bool(arm.call('nes_plan549_first',[arm.p]))== (not stop)
    if stop:
        assert not arm.call('nes_plan200_end',[arm.p]) and not sizes()
    else:
        assert arm.call('nes_plan200_end',[arm.p]) and arm.call('nes_plan200_progress',[arm.p,1])
        assert sizes()==([2,number] if not warm else [number+1,1])
        assert not arm.call('nes_plan200_retire',[arm.p]) and not arm.endpoint.rearmed
    return dict(warm=warm,count=number,stop=stop,accepted_E9_counts=sizes())


def suffix(src,slots,stop):
    arm=StopARM(src,'normal')
    arm.endpoint=Endpoint()
    arm.setup()
    records=[record(1,slot,100+i) for i,slot in enumerate(slots)]
    for q in records[:15]:
        arm.u.mem_write(arm.q,q)
        assert arm.call('nes_plan200_emit',[arm.p,arm.q])
    first=next(bytes.fromhex(t) for t in arm.endpoint.calls if t.startswith('e9'))
    sorted15=sorted(records[:15],key=lambda q:q[2])
    cut=14
    while cut and sorted15[cut][2]==sorted15[cut-1][2]+1:
        cut-=1
    expected=cut if 0<cut<=7 else 15
    assert first[3]==expected and first[4:-4]==b''.join(map(wire_plan,sorted15[:expected]))
    arm.stopped=stop
    arm.u.mem_write(arm.q,records[15])
    assert bool(arm.call('nes_plan200_emit',[arm.p,arm.q]))==(not stop)
    assert bool(arm.call('nes_plan200_end',[arm.p]))==(not stop)
    sent=[bytes.fromhex(t) for t in arm.endpoint.calls if t.startswith('e9')]
    if stop:
        assert len(sent)==1 and not arm.endpoint.rearmed
    else:
        tail=sorted(sorted15[expected:]+records[15:],key=lambda q:q[2])
        assert len(sent)==2 and sent[1][3]==len(tail)+1
        assert sent[1][4:-4]==b''.join(map(wire_plan,tail+[record(3,0,0)]))
    return dict(cut=expected,counts=[t[3] for t in sent],stopped=stop)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--keep-run',action='store_true')
    a=p.parse_args()
    rows=[run(a.arm,True,k,False) for k in (1,2,3)]
    rows.extend((run(a.arm,False,2,False),run(a.arm,True,2,True)))
    if a.keep_run:
        slots=[39,40,27,41,42,43,29,44,31,45,46,34,47,48,49,50]
        rows.extend(suffix(a.arm,slots,stop) for stop in (False,True))
        rows.append(suffix(a.arm,list(range(16)),False))
        rows.append(suffix(a.arm,[0,0,2,2,*range(10,22)],False))
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),rows=rows),indent=2)+'\n')
