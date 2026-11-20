"""Couple the linked scheduler to both consumers, with a one-read control."""
import argparse
from pathlib import Path
from unittest.mock import patch

from replay_nes_table877 import replay, dense
from replay_nes_strip869 import run as coupled
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R1


def run(temp,phase,work,clip,credit_only):
    tag='880-credit' if credit_only else '880-progress'
    if not credit_only:
        return replay(temp,phase,work,tag,clip)
    # Keep the startup image, code addresses, guard and first full receipt
    # identical. Change only the read limit at the new call site.
    runtime=dense.joint.Runtime
    init=runtime.__init__
    hits=[]
    def attach(cpu,args,link):
        init(cpu,args,link)
        pc=cpu.syms['wait_map880'] & ~1
        def one(u,at,size,ctx):
            limit=u.reg_read(UC_ARM_REG_R1)
            assert limit in (96,120)
            if limit==96:
                hits.append(cpu.generation)
                u.reg_write(UC_ARM_REG_R1,1)
        cpu.u.hook_add(UC_HOOK_CODE,one,begin=pc,end=pc)
    with patch.object(runtime,'__init__',attach):
        coupled(temp,phase,work,tag,clip)
    if clip=='dense':assert 950 in hits


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('work',type=lambda s:Path(s).resolve())
    p.add_argument('clip',choices=('dense','opening','transition'))
    p.add_argument('--credit-only',action='store_true')
    run(**vars(p.parse_args()))
