"""Check the newly admitted ordinary-credit callback against the final linked ELF."""
import argparse
import json
from pathlib import Path

from guard_nes_credit876 import check as table_credit
from guard_nes_progress870 import Machine, offsets, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0


def check(src):
    m=Machine(src,bytes(128))
    rt,guard=0x20012000,0x0807ffc0
    fields=offsets(src,'nes_native_runtime165')
    window=offsets(src,'nes_sink_window184')
    plan=offsets(src,'nes_plan200')
    state=m.state+m.layout['nes_native165']['state']
    token=m.state+m.layout['nes_native165']['next_token']
    budget=rt+fields['prefetch_left']
    def hook(u,pc,size,_):
        if pc==guard:
            ok=case!='stop_before' and not (case=='stop_after' and 'poll' in events)
            events.append('guard')
        elif pc==m.syms['nes_cost474_pause']:
            ok=True
            events.append('pause')
        else:
            assert m.state_value()==0
            events.append('poll')
            ok=case!='read_error'
            if ok and case!='empty':
                u.mem_write(token,b'\x01\x00')
        u.reg_write(UC_ARM_REG_R0,int(ok))
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    for pc in (guard,m.syms['nes_cost474_pause'],m.syms['nes_native165_poll']):
        m.u.hook_add(UC_HOOK_CODE,hook,begin=pc,end=pc)
    rows={}
    for case in ('palette','OAM','table','empty','map','OBJ','unfinished','unprepared','spent',
                 'receiving','complete','stop_before','stop_after','read_error'):
        m.u.mem_write(rt,bytes(2048))
        m.u.mem_write(rt+fields['receiver'],m.state.to_bytes(4,'little'))
        m.u.mem_write(rt+fields['resident'],m.resident.to_bytes(4,'little'))
        m.u.mem_write(state,bytes([{'receiving':1,'complete':2}.get(case,0)]))
        m.u.mem_write(token,bytes(2))
        m.u.mem_write(budget,bytes([6 if case=='spent' else 7]))
        m.u.mem_write(rt+fields['plan']+plan['finished'],bytes([case!='unfinished']))
        m.u.mem_write(m.resident+m.layout['nes_resident211']['prepared'],bytes([case!='unprepared']))
        section={'map':2,'OBJ':1,'OAM':4,'table':5}.get(case,3)
        m.u.mem_write(rt+fields['transport']+window['last'],bytes([7 if case=='OBJ' else 2,section]))
        events=[]
        ok=m.call('wait634',[rt,guard|1,0,1])
        reads=case in ('palette','OAM','table','empty','stop_after','read_error')
        assert events.count('poll')==reads and bool(ok)==(case not in ('stop_before','stop_after','read_error'))
        left=m.u.mem_read(budget,1)[0]
        assert left==(6 if case in ('palette','OAM','table','spent','stop_after') else 7),(case,left)
        rows[case]=[events,left,bool(ok)]
    return dict(ordinary=rows,existing_table=table_credit(src,retry=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('src',type=Path)
    p.add_argument('out',type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(check(a.src),indent=2)+'\n')
