"""Timestamp successful ARM poll returns, including the validated END block."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from replay_nes_strip869 import dense, run
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R0


def replay(temp,phase,work,tag,clip):
    if clip!='dense':
        return run(temp,phase,work,tag,clip)
    runtime=dense.joint.Runtime
    init=runtime.__init__
    rows=[]
    def attach(cpu,args,link):
        init(cpu,args,link)
        sites=set()
        active=None
        def returned(u,pc,size,ctx):
            nonlocal active
            if active is None or active[0]!=pc:
                return
            _,receiver,start=active
            active=None
            if cpu.input_generation==951 and u.reg_read(UC_ARM_REG_R0):
                state=u.mem_read(receiver+cpu.layout['nes_native165']['state'],1)[0]
                rows.append(dict(start=start,end=round(cpu.clock),state=state))
        def entered(u,pc,size,ctx):
            nonlocal active
            if cpu.generation not in (950,951):
                return
            site=u.reg_read(UC_ARM_REG_LR)&~1
            assert active is None
            active=site,u.reg_read(UC_ARM_REG_R0),round(cpu.clock)
            if site not in sites:
                sites.add(site)
                u.hook_add(UC_HOOK_CODE,returned,begin=site,end=site)
        pc=cpu.syms['nes_native165_poll']
        cpu.u.hook_add(UC_HOOK_CODE,entered,begin=pc,end=pc)
    with patch.object(runtime,'__init__',attach):
        run(temp,phase,work,tag,clip)
    assert any(r['state']==2 for r in rows)
    (work/f'poll951-p{phase}.json').write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('work',type=lambda s:Path(s).resolve())
    p.add_argument('tag')
    p.add_argument('clip',choices=('dense','opening','transition'))
    replay(**vars(p.parse_args()))
