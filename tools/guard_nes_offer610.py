"""Verify the linked END path offers a quiet map only after checked bulk submission."""
import argparse
import json
from pathlib import Path
from check_nes_supply485_arm import ARM,sha,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_R0
from check_nes_game478 import UC_HOOK_CODE
from test_nes_bulk497_arm import Endpoint

def check(src,mode,kind=1):
    arm=ARM(src,'normal');arm.endpoint=Endpoint();arm.setup()
    arm.endpoint.jobs=[(kind,0,32 if kind else 16,0)];arm.endpoint.token=1
    for key,value,size in [('started',1,1),('generation',907,2),('quiet_map',0x0807ffa1,4)]:
        arm.put(arm.p,'nes_plan200',key,value,size)
    seen=[]
    def offered(u,pc,size,user):
        assert arm.endpoint.bulk==1
        assert arm.get(arm.p,'nes_plan200','bulk_pending')
        assert arm.get(arm.w,'nes_sink_window184','sent',2)==1
        assert not arm.endpoint.accepted
        seen.append(arm.instructions)
        arm.put(arm.p,'nes_plan200','quiet_map',0,4)
        if mode=='STOP':
            arm.endpoint.mode='STOP_after_bulk'
        elif mode=='bad_ACK':
            arm.endpoint.mode=mode
        u.reg_write(UC_ARM_REG_R0,1)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    arm.u.hook_add(UC_HOOK_CODE,offered,begin=0x0807ffa0,end=0x0807ffa0)
    ok=bool(arm.call('nes_plan200_end',[arm.p]))
    assert bool(seen)==bool(kind)
    if ok:ok=bool(arm.call('nes_plan200_progress',[arm.p,1]))
    assert ok==(mode=='normal'),(mode,ok)
    assert not arm.call('nes_plan200_retire',[arm.p])
    assert not arm.endpoint.rearmed and not arm.get(arm.s,'nes_native_sink165','displayed')
    return dict(mode=mode,kind=kind,callback_after_bulk=len(seen),END=ok,
                sent=arm.endpoint.sent,retired=arm.endpoint.retired)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--obj-only',action='store_true')
    a=p.parse_args()
    rows=[check(a.arm,n) for n in ('normal','STOP','bad_ACK')]
    if a.obj_only:rows.append(check(a.arm,'normal',0))
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),rows=rows),indent=2)+'\n')
