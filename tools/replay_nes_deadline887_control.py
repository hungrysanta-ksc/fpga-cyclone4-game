"""Replay one final-ACK wait with a shorter quiet interval on the original 886 boot."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from replay_nes_coverage886 import replay, run as run886
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP


def run(temp, scene):
    generation = {'dense': 945, 'opening': 916}[scene]
    runtime = replay.dense.joint.Runtime
    init = runtime.__init__
    calls = []

    def attach(cpu, args, link):
        init(cpu, args, link)
        saved = None
        returns = set()

        def restore(u, pc, size, ctx):
            nonlocal saved
            if saved and pc == saved[0]:
                u.mem_write(saved[1], saved[2])
                saved = None

        def enter(u, pc, size, ctx):
            nonlocal saved
            if cpu.generation != generation or u.reg_read(UC_ARM_REG_R2) != 2 or u.reg_read(UC_ARM_REG_R3):
                return
            sp = u.reg_read(UC_ARM_REG_SP)
            original = bytes(u.mem_read(sp, 4))
            assert saved is None and int.from_bytes(original, 'little') in (84*96, 84*128)
            ret = u.reg_read(UC_ARM_REG_LR) & ~1
            saved = ret, sp, original
            if ret not in returns:
                u.hook_add(UC_HOOK_CODE, restore, begin=ret, end=ret)
                returns.add(ret)
            calls.append(round(cpu.clock))
            u.mem_write(sp, (84*48).to_bytes(4, 'little'))

        pc = cpu.syms['nes_cost474_pause']
        cpu.u.hook_add(UC_HOOK_CODE, enter, begin=pc, end=pc)

    original_run = replay.run
    tag = '887-local'

    def rename(temp, phase, work, oldtag, clip):
        assert oldtag == '886-static'
        return original_run(temp, phase, work, tag, clip)

    with patch.object(runtime, '__init__', attach), patch.object(replay, 'run', rename):
        run886(temp, 2, scene, False)
    assert calls
    clip = 'demo' if scene == 'dense' else scene
    (temp / f'nes-tile821-{clip}-jointmirror-p2-{tag}/calls887.json').write_text(json.dumps(calls))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp', type=Path)
    p.add_argument('scene', choices=('dense','opening'))
    run(**vars(p.parse_args()))
