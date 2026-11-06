# SPDX-License-Identifier: MIT
"""Same binary and clocks, bypass only the optional palette drain calls on 957."""
import json
import runpy
from unittest.mock import patch

from check_nes_game478 import UC_HOOK_CODE, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0
from test_nes_raw506_joint import Runtime


if __name__=='__main__':
    init=Runtime.__init__
    cuts=[]
    outputs=[]
    def observe(machine,args,link):
        init(machine,args,link)
        outputs.append(args.out)
        first=machine.syms['packet_wire']
        limit=min(x for x in machine.syms.values() if x>first)
        def bypass(u,pc,size,unused):
            ret=u.reg_read(UC_ARM_REG_LR)
            if machine.generation==957 and first<=(ret&~1)-2<limit:
                w=u.reg_read(UC_ARM_REG_R0)
                head=bytes(u.mem_read(w+machine.layout['nes_sink_window184']['last'],10))
                assert head[:2]==bytes([4,3]) and int.from_bytes(head[8:10],'little')==957
                cuts.append(machine.clock)
                u.reg_write(UC_ARM_REG_R0,1)
                u.reg_write(UC_ARM_REG_PC,ret)
        pc=machine.syms['nes_window184_drain']
        machine.u.hook_add(UC_HOOK_CODE,bypass,begin=pc,end=pc)
    with patch.object(Runtime,'__init__',observe):
        runpy.run_module('test_nes_board611',run_name='__main__')
    assert len(outputs)==1 and len(cuts) in (0,4)
    (outputs[0]/'control.json').write_text(json.dumps(dict(bypassed_at=cuts))+'\n')
