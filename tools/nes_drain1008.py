"""Measure ARM drain callers around the checked 912 token 36 receipt."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from nes_capture978 import work
from nes_plan975 import simulate
from replay_nes_supply905 import joint, UC_HOOK_CODE, UC_ARM_REG_LR


def measure(temp,phase):
    init=joint.Runtime.__init__
    log=[]
    def install(cpu,*args):
        init(cpu,*args)
        pc=cpu.syms['nes_window184_drain']
        functions=sorted((addr,name) for name,addr in cpu.syms.items() if addr<=0x1fffffff)
        def sample(u,at,size,ctx):
            if cpu.generation==912:
                caller=(u.reg_read(UC_ARM_REG_LR)&~1)-2
                base,name=max((a,n) for a,n in functions if a<=caller)
                log.append([cpu.clock,name,caller-base])
        cpu.u.hook_add(UC_HOOK_CODE,sample,begin=pc,end=pc)
    with patch.object(joint.Runtime,'__init__',install):
        simulate(temp,phase,'cold',True,work('returned'),True,tag='1008drain',edition=966)
    (temp/f'nes-drain1008-p{phase}.json').write_text(json.dumps(log))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2))
    a=p.parse_args()
    measure(a.temp,a.phase)
