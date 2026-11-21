"""Route one ordinary credit callback to the existing checked receiver in generation 962."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from replay_nes_strip869 import dense, run
from guard_nes_progress870 import offsets
from check_nes_strip869 import digest
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R2, UC_ARM_REG_R3


def replay(temp, phase, work, policy):
    src = work/'link-credit/src'
    assert digest(src/'obj-nes-100/firmware.stm') == 'e718bd94d0da27dbc5ab66081b31a34460bda3dbb0a22c2d9965c48f92c6ba9d'
    plan, queue = [offsets(src, name) for name in
        ('nes_plan200','nes_sink_window184')]
    runtime = dense.joint.Runtime
    original = runtime.__init__
    changes = []
    def attach(cpu, args, link):
        original(cpu, args, link)
        rt, rx, resident = [cpu.layout[k] for k in ('nes_native_runtime165','nes_native165','nes_resident211')]
        def wait(u, pc, size, _):
            if changes or cpu.generation != 962 or u.reg_read(UC_ARM_REG_R2) != 0 or not u.reg_read(UC_ARM_REG_R3):
                return
            ctx = u.reg_read(UC_ARM_REG_R0)
            def read(addr, n=1):
                return int.from_bytes(u.mem_read(addr,n),'little')
            sink = ctx + rt['transport']
            receiver = read(ctx + rt['receiver'],4)
            owner = read(ctx + rt['resident'],4)
            header = bytes(u.mem_read(sink + queue['last'],10))
            if not (read(ctx + rt['plan'] + plan['finished']) and owner and read(owner + resident['prepared'])
                    and read(ctx + rt['prefetch_left']) == 6 and read(receiver + rx['state']) == 1):
                return
            if header[1] != (3 if policy == 'palette' else 5):
                return
            changes.append(dict(clock=round(cpu.clock), last_header=header.hex(),
                                input_generation=cpu.input_generation, left=6))
            u.reg_write(UC_ARM_REG_R2,4)
        pc = cpu.syms['wait634']
        cpu.u.hook_add(UC_HOOK_CODE,wait,begin=pc,end=pc)
    tag = '885-' + policy
    with patch.object(runtime,'__init__',attach):
        run(temp,phase,work,tag,'dense')
    assert len(changes) == 1 and changes[0]['input_generation'] == 963, changes
    (temp/f'nes-tile821-demo-jointmirror-p{phase}-{tag}'/'credit885.json').write_text(json.dumps(changes)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('phase',type=int,choices=(1,2))
    parser.add_argument('work',type=lambda s:Path(s).resolve())
    parser.add_argument('policy',choices=('palette','table'))
    replay(**vars(parser.parse_args()))
