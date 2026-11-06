"""Time the linked receiver's real packet CRC and decode without adding MCU instructions."""
import argparse
import runpy
import sys
from contextlib import ExitStack
from unittest.mock import patch
from check_nes_game478 import UC_HOOK_CODE,UC_ARM_REG_LR,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3
import test_nes_raw506_joint as joint
from nes_geometry650 import encode


def observe(original):
    def init(cpu,args,link):
        original(cpu,args,link)
        active={}
        exits=set()
        def finish(u,pc,size,unused):
            for name,(ret,index,start,ops) in list(active.items()):
                if ret==pc:
                    cpu.events.append(dict(event="block650",part=name,generation=cpu.generation,input_generation=955,
                                           index=index,start=start,clock=cpu.clock,ops=cpu.instructions-ops))
                    del active[name]
        def enter(u,pc,size,name):
            if cpu.input_generation!=955 or cpu.index>=7 or name in active:return
            expected=cpu.packets[cpu.index]
            if name=="restore":
                addr=u.reg_read(UC_ARM_REG_R2);n=u.reg_read(UC_ARM_REG_R3)
            else:
                if "restore" in active:return
                addr=u.reg_read(UC_ARM_REG_R1);n=u.reg_read(UC_ARM_REG_R2)
            if n!=len(expected) or bytes(u.mem_read(addr,n))!=expected:return
            ret=u.reg_read(UC_ARM_REG_LR)&~1
            if ret not in exits:
                exits.add(ret);u.hook_add(UC_HOOK_CODE,finish,begin=ret,end=ret)
            active[name]=(ret,cpu.index,cpu.clock,cpu.instructions)
        for symbol,part in (("nes_native165_packet","restore"),("crc_xmodem_block","wire_crc")):
            pc=cpu.syms[symbol]
            cpu.u.hook_add(UC_HOOK_CODE,enter,part,begin=pc,end=pc)
    return init


if __name__=="__main__":
    p=argparse.ArgumentParser(add_help=False)
    p.add_argument("--geometry650",action="store_true")
    p.add_argument("--held649",action="store_true")
    options,rest=p.parse_known_args();sys.argv[1:]=rest
    with ExitStack() as stack:
        stack.enter_context(patch.object(joint.Runtime,"__init__",observe(joint.Runtime.__init__)))
        if options.geometry650:
            # The shared schedule installs its default packetizer during
            # setup. Bind at the actual production call, after that setup.
            begin=joint.Runtime.begin_input
            def produce(cpu,generation=None):
                with patch.object(joint,"encode",encode):
                    begin(cpu,generation)
                if cpu.input_generation==955:
                    assert cpu.packets[0][12:14]==b"\xff\xff"
                    assert all(block[:2]==b"\xff\xff" for block in cpu.packets[1:7])
            stack.enter_context(patch.object(joint.Runtime,"begin_input",produce))
        runpy.run_module("test_nes_receive649" if options.held649 else "test_nes_tail648",run_name="__main__")
