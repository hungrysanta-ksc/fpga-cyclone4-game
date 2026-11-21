"""Test admission of a receiver poll at a queue return on the final ARM ELF."""
import argparse
import json
from pathlib import Path

from guard_nes_progress870 import Machine, offsets, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R3


def check(src, retry, pause=False):
    m=Machine(src,bytes(128))
    rt=0x20012000
    check_pc=0x0807ffc0
    fields=offsets(src,'nes_native_runtime165')
    window=offsets(src,'nes_sink_window184')
    state=m.state+m.layout['nes_native165']['state']
    token=m.state+m.layout['nes_native165']['next_token']
    prepared=m.resident+m.layout['nes_resident211']['prepared']
    last=rt+fields['transport']+window['last']
    def callback(u,pc,size,ctx):
        if pc==check_pc:
            events.append('guard')
            ok=case!='stop_before_read' and not (case=='stop_after_read' and 'poll' in events)
        elif pc==m.syms['nes_cost474_pause']:
            events.append('pause_progress' if u.reg_read(UC_ARM_REG_R3) else 'pause')
            ok=True
        else:
            assert m.state_value()==0
            events.append('poll')
            if case!='empty':
                u.mem_write(token,b'\x01\0')
            ok=case!='read_error'
        u.reg_write(UC_ARM_REG_R0,int(ok))
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    for pc in (check_pc,m.syms['nes_native165_poll'],m.syms['nes_cost474_pause']):
        m.u.hook_add(UC_HOOK_CODE,callback,begin=pc,end=pc)
    result={}
    for case in ('ready','empty','planner_owns','pending_credit','different_section',
                 'bulk_header','receiving','complete','other_wait','stop_before_read',
                 'stop_after_read','read_error'):
        if pause and case=='stop_after_read':
            continue
        m.u.mem_write(rt,bytes(2048))
        m.u.mem_write(rt+fields['receiver'],m.state.to_bytes(4,'little'))
        m.u.mem_write(rt+fields['resident'],m.resident.to_bytes(4,'little'))
        m.u.mem_write(state,bytes([{'receiving':1,'complete':2}.get(case,0 if retry or pause else 4)]))
        m.u.mem_write(rt+fields['prefetch_left'],bytes([7 if retry or pause else 0]))
        m.u.mem_write(prepared,bytes([case!='planner_owns']))
        m.u.mem_write(last,bytes([7 if case=='bulk_header' else 2,2 if case=='different_section' else 5]))
        m.u.mem_write(token,bytes(2))
        events=[]
        reason=int(case=='other_wait') if pause else int(case!='other_wait')
        progress=int(case=='pending_credit') if pause else int(case!='pending_credit')
        ok=m.call('wait634',[rt,check_pc|1,reason,progress])
        assert bool(ok)==(case not in ('stop_before_read','stop_after_read','read_error')), (case,events)
        expected=case in ('ready','empty','stop_after_read','read_error')
        assert events.count('poll')==int(expected),(case,events)
        if case in ('ready','empty'):
            tail=('pause_progress' if case=='ready' else 'pause') if pause else 'guard'
            assert events==['guard','poll',tail] and m.u.mem_read(rt+fields['prefetch_left'],1)[0]==(6 if case=='ready' else 7)
        result[case]=dict(events=events,success=bool(ok))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('src',type=Path)
    parser.add_argument('out',type=Path)
    parser.add_argument('--retry',action='store_true')
    parser.add_argument('--pause',action='store_true')
    args=parser.parse_args()
    args.out.write_text(json.dumps(check(args.src,args.retry,args.pause),indent=2)+'\n')
