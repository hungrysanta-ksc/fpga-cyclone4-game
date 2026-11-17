"""Sensitivity only: remove time for map payload wire bits, keeping their contents and all receipts."""
from pathlib import Path
import argparse
import sys
from unittest.mock import patch
from replay_nes_tile821 import joint, main, WORK
from replay_nes_output822 import MirrorLink
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_R3


def run(phase,temp,budget):
    original=joint.Runtime.hook
    def discount(cpu,u,at,size,user):
        if at!=cpu.spi:
            return original(cpu,u,at,size,user)
        n=u.reg_read(UC_ARM_REG_R3)
        tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),n))
        if tx[:3]!=bytes((0xe1,2,2)) or int.from_bytes(tx[9:11],"little")!=909:
            return original(cpu,u,at,size,user)
        wire=int.from_bytes(tx[13:15],"little")
        old=cpu.driver_extra[0xe1]
        cpu.driver_extra[0xe1]-=wire*8*joint.MASTER/2625000
        try:
            return original(cpu,u,at,size,user)
        finally:
            cpu.driver_extra[0xe1]=old
    with patch.object(sys,"argv",["replay","","","","","","830free",str(budget)]),patch.object(joint.Runtime,"hook",discount):
        main(WORK.parent/"nes-tile821/demo-extra01","demoB","jointmirror",phase,temp,
             arm=WORK.parent/"nes-output823/link-826/src",link_class=MirrorLink)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("temp",type=Path);p.add_argument("budget",type=Path)
    run(**vars(p.parse_args()))
