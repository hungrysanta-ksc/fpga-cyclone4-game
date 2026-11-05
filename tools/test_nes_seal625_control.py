# SPDX-License-Identifier: MIT
"""Leave seven plans queued at the single 955 BG-to-OBJ transition."""
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
        def bypass(u,at,size,unused):
            if machine.generation!=955:
                return
            plan=u.reg_read(UC_ARM_REG_R0)
            assert plan==machine.rt+machine.layout['nes_native_runtime165']['plan']
            val=lambda key,n: int.from_bytes(u.mem_read(plan+machine.layout['nes_plan200'][key],n),'little')
            if val('sent',2)!=1 or val('count',1)!=7 or val('ending',1):
                return
            n=val('bytes',2)
            if n-val('obj_start',1)!=8:
                return
            assert not cuts and val('bank_history',1)==2
            cuts.append(machine.clock)
            u.reg_write(UC_ARM_REG_R0,1)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        pc=machine.syms['flush']
        machine.u.hook_add(UC_HOOK_CODE,bypass,begin=pc,end=pc)
    with patch.object(Runtime,'__init__',observe):
        runpy.run_module('test_nes_board611',run_name='__main__')
    assert len(cuts)==len(outputs)==1
    (outputs[0]/'control.json').write_text(json.dumps(dict(bypassed_at=cuts[0]))+'\n')
