"""Keep the identical boot and prefix, and send the transition-952 OAM head late."""
import argparse
from pathlib import Path
from unittest.mock import patch

from replay_nes_strip869 import dense, run
from check_nes_strip869 import digest
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_CPSR


def control(temp, phase, work):
    assert digest(work/'link-credit/src/obj-nes-100/firmware.stm') == 'dc32f22316292b37c56de00b8aaa3c85659044956054113defda6e6139ec6ed9'
    runtime = dense.joint.Runtime
    original = runtime.__init__
    hits = []

    def attach(cpu, args, link):
        original(cpu, args, link)
        # ORRS of map_upload halves, then BNE to the late reuse path.
        branch = 0x0801ee8a
        assert bytes(cpu.u.mem_read(branch - 2, 6)) == bytes.fromhex('0b4340f09c80')

        def late(u, address, size, ctx):
            if cpu.generation == 952:
                flags = u.reg_read(UC_ARM_REG_CPSR)
                assert flags & (1 << 30)
                u.reg_write(UC_ARM_REG_CPSR, flags & ~(1 << 30))
                hits.append(cpu.generation)

        cpu.u.hook_add(UC_HOOK_CODE, late, begin=branch, end=branch)

    with patch.object(runtime, '__init__', attach):
        run(temp, phase, work, '882-late952', 'transition')
    assert hits == [952]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp', type=Path)
    parser.add_argument('phase', type=int, choices=(1, 2))
    parser.add_argument('work', type=lambda s: Path(s).resolve())
    control(**vars(parser.parse_args()))
