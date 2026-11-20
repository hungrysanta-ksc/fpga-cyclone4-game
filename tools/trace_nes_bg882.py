"""Record cold BG cache misses and calendar grants without changing either executable."""
import argparse
import csv
import json
from pathlib import Path
from unittest.mock import patch

from replay_nes_strip869 import run
from replay_nes_output852 import MirrorLink, joint


def collect(temp, phase, work, version):
    tag = f'882-cold-{version}'
    dst = temp / f'nes-tile821-opening-jointmirror-p{phase}-{tag}'
    original_call = joint.Runtime.call
    original_read = MirrorLink.next_rom
    rows = []

    class PrefixComplete(Exception):
        pass

    def step(cpu, name, args, *rest, **kw):
        if name == 'nes_runtime165_step' and cpu.generation == 907:
            raise PrefixComplete()
        return original_call(cpu, name, args, *rest, **kw)

    def observe(link, t):
        kind, addr = link.pending[0]
        miss = kind == 0 and not (link.tag == addr // 16 and (addr & 15) in link.line)
        result = original_read(link, t)
        if miss and link.generation <= 906:
            req = t + 1
            grant, response = link.calendar.select(req - link.a.rom_phase)
            assert response + link.a.rom_phase == result
            rows.append((link.generation, addr, round(req), grant + link.a.rom_phase, result))
        return result

    with patch.object(MirrorLink, 'next_rom', observe), patch.object(joint.Runtime, 'call', step):
        try:
            run(temp, phase, work, tag, 'opening')
        except PrefixComplete:
            pass
        else:
            raise AssertionError('missing first step after the observed generations')
    with (dst / 'bg-grants.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['generation', 'address', 'request', 'grant', 'response'])
        writer.writerows(rows)
    full = temp / f'nes-tile821-opening-jointmirror-p{phase}-{version}'
    # The run exits at the next ARM step. Compare the complete observed SPI
    # prefix, including input received while the previous display was pending.
    def early_spi(path):
        return [e for e in json.loads((path/'events.json').read_bytes())
                if e['event'] == 'SPI' and e['generation'] <= 906]
    assert early_spi(dst) == early_spi(full)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp', type=Path)
    parser.add_argument('phase', type=int, choices=(1, 2))
    parser.add_argument('work', type=lambda s: Path(s).resolve())
    parser.add_argument('version', choices=('872-final','881-range'))
    collect(**vars(parser.parse_args()))
