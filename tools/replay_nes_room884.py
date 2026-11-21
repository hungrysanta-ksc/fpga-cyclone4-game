"""Observe the NES export and credit callbacks while output 962 owns the display."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from replay_nes_strip869 import dense, run
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_CPSR


def replay(temp, phase, work, tag, late962=False):
    runtime=dense.joint.Runtime
    init, offer=runtime.__init__, runtime.offer_input
    rows=[]
    def attach(cpu,args,link):
        init(cpu,args,link)
        def waiting(u,pc,size,_):
            if cpu.generation==962:
                rows.append(dict(event='credit_wait',clock=round(cpu.clock),
                                 reason=u.reg_read(UC_ARM_REG_R2),progress=bool(u.reg_read(UC_ARM_REG_R3))))
        pc=cpu.syms['wait634']
        cpu.u.hook_add(UC_HOOK_CODE,waiting,begin=pc,end=pc)

        if late962:
            # CMP r3,#2 / BHI only controls the new FINISH+ordinary-credit path.
            branch=pc+0x30
            assert bytes(cpu.u.mem_read(branch-2,4))==bytes.fromhex('022b08d8')
            def defer(u,at,size,_):
                if cpu.generation==962 and u.reg_read(UC_ARM_REG_R3)>2:
                    rows.append(dict(event='deferred',clock=round(cpu.clock)))
                    u.reg_write(UC_ARM_REG_CPSR,u.reg_read(UC_ARM_REG_CPSR)|(1<<30))
            cpu.u.hook_add(UC_HOOK_CODE,defer,begin=branch,end=branch)

    def observed(cpu):
        if cpu.generation!=962 or cpu.input_generation!=962:
            return offer(cpu)
        link=cpu.link
        row=dict(event='D0',clock=round(cpu.clock),ready=round(cpu.next_capture_ready),
                 prior_drained=cpu.index==len(cpu.packets),end=bool(link.end),
                 prepared=bool(cpu.prepared),todo=bool(link.todo),flight=bool(link.flight),
                 open=bool(link.open),jobs=bool(link.jobs))
        offer(cpu)
        row['exported']=cpu.input_generation==963
        rows.append(row)
    with patch.object(runtime,'__init__',attach),patch.object(runtime,'offer_input',observed):
        run(temp,phase,work,tag,'dense')
    assert sum(r.get('exported',False) for r in rows)==1
    out=temp/f'nes-tile821-demo-jointmirror-p{phase}-{tag}'
    (out/'credit962.json').write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('work',type=lambda s:Path(s).resolve())
    p.add_argument('tag')
    p.add_argument('--late962',action='store_true')
    replay(**vars(p.parse_args()))
