"""Causal control: reuse exactly one prior E8 snapshot after the 950 SEAL."""
import argparse
from pathlib import Path
from unittest.mock import patch

from replay_nes_strip869 import dense, run
from check_nes_strip869 import digest
from check_nes_game478 import crc
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2


def replay(temp,phase,work):
    assert digest(work/'link-credit/src/obj-nes-100/firmware.stm')=='033f7f93bafde2ed3c88f425dd2052c59c2723676ee09f4bf33877d9a81db1ea'
    init=dense.joint.Runtime.__init__
    used=[]
    def attach(cpu,args,link):
        init(cpu,args,link)
        pending=None
        snapshot=None
        sites=set()
        def returned(u,pc,size,ctx):
            nonlocal pending,snapshot
            if pending is not None and pc==pending[0]:
                _,buf=pending
                pending=None
                if u.reg_read(UC_ARM_REG_R0):
                    b=bytes(u.mem_read(buf,20))
                    if b[3]==2 and not any(b[6:19]):
                        assert b[1:3]==bytes((0xd7,4)) and b[19]==crc(b[1:19],8,7,0)
                        snapshot=b
        def read(u,pc,size,ctx):
            nonlocal pending
            if cpu.generation!=950:return
            mode=u.reg_read(UC_ARM_REG_R2)
            lr=u.reg_read(UC_ARM_REG_LR)
            buf=u.reg_read(UC_ARM_REG_R1)
            if mode==2:
                pc=lr&~1
                assert pending is None
                pending=pc,buf
                if pc not in sites:
                    sites.add(pc)
                    u.hook_add(UC_HOOK_CODE,returned,begin=pc,end=pc)
            elif mode==3:
                assert snapshot is not None and not used
                used.append((phase,round(cpu.clock)))
                u.mem_write(buf,snapshot)
                u.reg_write(UC_ARM_REG_R0,1)
                u.reg_write(UC_ARM_REG_PC,lr)
        pc=cpu.syms['read509']
        cpu.u.hook_add(UC_HOOK_CODE,read,begin=pc,end=pc)
    with patch.object(dense.joint.Runtime,'__init__',attach):
        run(temp,phase,work,'878-once','dense')
    assert len(used)==1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int)
    p.add_argument('work',type=lambda s:Path(s).resolve())
    replay(**vars(p.parse_args()))
