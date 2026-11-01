# SPDX-License-Identifier: MIT
"""Observe the linked output call and each list command on unchanged MMC529 schedules."""
import argparse
import json
from pathlib import Path

import test_nes_raw506_joint as joint
from trace_nes_map527 import CheckedLink, MapRuntime, observed, run_schedule
from check_nes_game478 import UC_HOOK_CODE, UC_ARM_REG_LR
from test_nes_quiet528 import seal_trace
from nes_raw506 import once


class OutputRuntime(MapRuntime):
    def __init__(self,a,link):
        super().__init__(a,link)
        self.return_pc=None
        def mark(name):
            self.events.append(dict(generation=self.generation,event=name,clock=self.clock))
        def leave(u,pc,size,user):
            mark('output_return531')
        def enter(u,pc,size,user):
            # The measured firmware calls this once per completed frame from runtime_step.
            ret=u.reg_read(UC_ARM_REG_LR)&~1
            if self.return_pc is None:
                self.return_pc=ret
                u.hook_add(UC_HOOK_CODE,leave,begin=ret,end=ret)
            assert self.return_pc==ret
            mark('output_enter531')
        pc=self.syms['nes_sink212_seal']
        self.u.hook_add(UC_HOOK_CODE,enter,begin=pc,end=pc)


def instrument(s,a):
    labels=json.loads((a.client/'labels.json').read_text())
    s=seal_trace(observed(s,a))
    s=once(s,' or (pw(8)~=952 and pw(8)~=954)','')
    hooks=[]
    for label,event,value in [('upload_loop212','command','i<word(0x1250) and word(0x4002+i) or -1'),
                              ('raw_dispatch489','raw_enter','0'),('raw_advance489','raw_done','0'),
                              ('final212','final_credit','word(0x1256)')]:
        hooks.append(f"emu.addMemoryCallback(function()local i=word(0x1252);log528('{event}',{value})end,emu.callbackType.exec,{labels[label]})")
    return once(s,'local function loaded()', '\n'.join(hooks)+'\nlocal function loaded()')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','data','fixture','plans','client','mesen','out','calendar','driver503','capture'):
        p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--start-clock',type=int,required=True)
    a=p.parse_args()
    a.map526=True
    joint.Runtime=OutputRuntime
    run_schedule(a,instrument,CheckedLink,frames=53)
