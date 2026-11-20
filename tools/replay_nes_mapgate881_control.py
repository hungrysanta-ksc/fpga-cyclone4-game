"""Restore the pre-881 scroll wait in the same image for a paired transition replay."""
import argparse
from pathlib import Path
from unittest.mock import patch

from replay_nes_strip869 import dense, run
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R1


def replay(temp, phase, work):
    runtime = dense.joint.Runtime
    original = runtime.__init__
    changed = []

    def attach(cpu, args, link):
        original(cpu, args, link)
        pc = cpu.syms['wait_map880'] & ~1

        def restore_limit(u, address, size, context):
            reads = u.reg_read(UC_ARM_REG_R1)
            assert reads in (1, 96, 120)
            if reads == 1:
                changed.append(cpu.generation)
                u.reg_write(UC_ARM_REG_R1, 96)

        cpu.u.hook_add(UC_HOOK_CODE, restore_limit, begin=pc, end=pc)

    with patch.object(runtime, '__init__', attach):
        run(temp, phase, work, '881-unconditional', 'transition')
    assert 941 in changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp', type=Path)
    parser.add_argument('phase', type=int, choices=(1, 2))
    parser.add_argument('work', type=lambda s: Path(s).resolve())
    replay(**vars(parser.parse_args()))
