"""Observe the current receiver owner and tile drain on the coupled ARM replay."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from replay_nes_strip869 import dense, run
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R2, UC_ARM_REG_R3


def replay(temp, phase, work, tag, clip):
    if clip!='dense':
        return run(temp,phase,work,tag,clip)
    runtime=dense.joint.Runtime
    original=runtime.__init__
    rows=[]
    def observe(cpu, args, link):
        original(cpu,args,link)
        rt=cpu.layout['nes_native_runtime165']
        def read(base,offset,size=1):
            return int.from_bytes(cpu.u.mem_read(base+offset,size),'little')
        def watch(name):
            def record(u,pc,size,ctx):
                if cpu.generation!=950 or cpu.input_generation!=950:
                    return
                receiver=read(cpu.rt,rt['receiver'],4)
                resident=read(cpu.rt,rt['resident'],4)
                if not receiver or not resident:
                    return
                row=dict(clock=round(cpu.clock),event=name,
                         state=read(receiver,cpu.layout['nes_native165']['state']),
                         prepared=read(resident,cpu.layout['nes_resident211']['prepared']),
                         prefetch_left=read(cpu.rt,rt['prefetch_left']),
                         capture_ready=cpu.next_capture_ready,end=bool(link.end),
                         jobs=len(link.jobs),flight=bool(link.flight),open=bool(link.open),todo=len(link.todo))
                if name=='wait634':
                    row.update(reason=u.reg_read(UC_ARM_REG_R2),progress=u.reg_read(UC_ARM_REG_R3)&1)
                rows.append(row)
            pc=cpu.syms[name]
            cpu.u.hook_add(UC_HOOK_CODE,record,begin=pc,end=pc)
        for name in ('wait634','nes_native165_poll','nes_sink212_seal','nes_resident211_prepare'):
            watch(name)
    with patch.object(runtime,'__init__',observe):
        run(temp,phase,work,tag,clip)
    assert any(row['event']=='nes_native165_poll' and row['prepared'] for row in rows)
    (work/f'ownership-{phase}.json').write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('work',type=lambda s:Path(s).resolve())
    p.add_argument('tag')
    p.add_argument('clip',choices=('dense','opening','transition'))
    replay(**vars(p.parse_args()))
