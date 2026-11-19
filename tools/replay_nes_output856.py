"""Observe output phase and poll spans on the two released links under one SPI calibration."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from prepare_nes_trial802 import PROBES
from replay_nes_column853 import joint, run
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3


def replay(temp, edition, phase):
    links = {
        826: ("nes-output823/link-826/src", "nes-output815/client"),
        855: ("nes-trial855/link/src", "nes-column854/client-e"),
    }
    arm, client = (PROBES / name for name in links[edition])
    original = joint.Runtime.__init__
    spans = []
    polls = []
    tag = f"856-{edition}-on"
    budget = Path.home() / "Downloads/nes-budget-mmc855.txt"

    def attach(cpu, *args):
        original(cpu, *args)
        active = []
        returns = set()

        def install(address, callback):
            cpu.u.hook_add(UC_HOOK_CODE, callback, begin=address, end=address)

        def phase_end(u, address, size, data):
            if u.reg_read(UC_ARM_REG_R0) == 2:
                now = int(cpu.clock * joint.ARM_HZ / joint.MASTER)
                elapsed = (now - u.reg_read(UC_ARM_REG_R1)) & 0xffffffff
                spans.append([cpu.clock - elapsed * joint.MASTER / joint.ARM_HZ, cpu.clock])

        def returned(u, address, size, data):
            if active and active[-1][0] == address:
                _, begin, reason, progress = active.pop()
                polls.append([begin, cpu.clock, reason, progress])

        def pause(u, address, size, data):
            lr = u.reg_read(UC_ARM_REG_LR) & ~1
            active.append((lr, cpu.clock, u.reg_read(UC_ARM_REG_R2), u.reg_read(UC_ARM_REG_R3)))
            if lr not in returns:
                returns.add(lr)
                install(lr, returned)

        install(cpu.syms["nes_cost471_phase"] & ~1, phase_end)
        install(cpu.syms["nes_cost474_pause"] & ~1, pause)

    with patch.object(joint.Runtime, "__init__", attach):
        run(temp, "demo", phase, True, tag, arm=arm, client=client, budget=budget)
    out = temp / f"nes-tile821-demo-jointmirror-p{phase}-{tag}"
    assert len(spans) == 62 and polls
    (out / "output-spans.json").write_text(json.dumps(dict(phases=spans, polls=polls)))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp", type=Path)
    p.add_argument("edition", type=int, choices=(826, 855))
    p.add_argument("phase", type=int, choices=(1, 2))
    a = p.parse_args()
    replay(a.temp, a.edition, a.phase)
