"""Capture one cold ARM/65816 SPI conversation for the RUN entry replay."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from replay_nes_strip869 import map_samples
from replay_nes_column853 import run
import replay_nes_column853 as runner
from check_nes_game478 import sha
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_PC


class Retired(Exception):
    pass


def capture(temp, out):
    root = Path(__file__).resolve().parents[2] / 'probes'
    arm = root / 'nes-reset892/link/src'
    client = root / 'nes-trial890/client02'
    rows = []
    original_hook = runner.joint.Runtime.hook
    original_call = runner.joint.Runtime.call
    original_main = runner.main

    def main(*args, **kw):
        template = kw['adapt_template']
        kw['adapt_template'] = lambda s: map_samples(template(s))
        return original_main(*args, **kw)

    def hook(cpu, u, at, size, user):
        if not cpu.live or at != cpu.spi:
            return original_hook(cpu, u, at, size, user)
        n = u.reg_read(UC_ARM_REG_R3)
        addr = u.reg_read(UC_ARM_REG_R2)
        tx = bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1), n))
        original_hook(cpu, u, at, size, user)
        if u.reg_read(UC_ARM_REG_PC) == at:
            return  # IRQ scheduled before servicing SPI
        rows.append([tx.hex(), bytes(u.mem_read(addr, n)).hex()])
    def call(cpu,name,args):
        if name=='nes_runtime165_begin':
            args=[*args[:-2],0xa58fe808,args[-1]]
        result=original_call(cpu,name,args)
        if name=='nes_runtime165_step' and cpu.generation!=905:
            assert result==1
            raise Retired
        return result

    with patch.object(runner, 'main', main), patch.object(runner.joint.Runtime, 'hook', hook), patch.object(runner.joint.Runtime,'call',call):
        try:
            run(temp, 'opening', 1, True, out.stem, arm=arm, client=client,
                budget=Path.home()/'Downloads/nes-budget-mmc855.txt')
        except Retired:
            assert any(row[0].startswith('ea') for row in rows) and rows[-1][0].startswith('e8')
        else:
            raise AssertionError('first retire missing')
    out.write_text(json.dumps(dict(firmware=sha(arm/'obj-nes-100/firmware.stm'),
                                   client=sha(client/'sink165.sfc'), transactions=rows)))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp', type=Path)
    p.add_argument('out', type=Path)
    a = p.parse_args()
    capture(a.temp, a.out)
