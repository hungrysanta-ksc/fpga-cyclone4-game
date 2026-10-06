# SPDX-License-Identifier: MIT
"""Test the055 comparator with explicitly synthetic copies of053 evidence.

This does not run RTL or count as a new SPI/core execution. Original evidence is
read only. A permitted constant timestamp offset must not hide a changed event
or changed pixel. All synthetic fixtures remain in the requested private output.
"""
from pathlib import Path
import argparse, json, shutil
from nes_spi_live import compare_case, sha, put

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    assert not a.out.exists()
    case = 'banks32'
    c = a.out / case
    c.mkdir(parents=True)
    for n in ['prg.hex', 'chr.hex', 'manifest.json', 'simulation.log', 'live.tsv',
              *[f'frame-{i}.hex' for i in range(1, 5)]]:
        shutil.copy2(a.baseline / case / n, c / n)
    with (c / 'simulation.log').open('a') as f:
        f.write('\nSYNTHETIC COMPARATOR FIXTURE: not a new RTL run\n')
        f.write('SPI BOOT bytes=98304 pin_writes=98304 run=1\n')
    rows = [s.split() for s in (c / 'live.tsv').read_text().splitlines()]
    payload = [r for r in rows if r[0] == 'B']
    for r in rows:
        if r[0] != 'B':
            j = 4 if r[0] == 'E' else 2
            r[j] = str(int(r[j]) + 7)
    for i in range(4):
        b = payload[2008*i+12:2008*i+16]
        tick = int.from_bytes(bytes(int(r[2]) for r in b), 'little') + 7
        for r, value in zip(b, tick.to_bytes(4, 'little')): r[2] = str(value)
    shifted = '\n'.join(' '.join(r) for r in rows) + '\n'
    put(c / 'live.tsv', shifted)
    result = compare_case(a.out, a.baseline, case)
    assert result['tick_offsets_vs053'] == [7] * 4
    def must_reject(label):
        try: compare_case(a.out, a.baseline, case)
        except AssertionError: return label
        raise AssertionError('Comparator accepted ' + label)
    e = next(r for r in rows if r[0] == 'E')
    e[4] = str(int(e[4]) + 1)
    put(c / 'live.tsv', '\n'.join(' '.join(r) for r in rows) + '\n')
    rejected = [must_reject('one event tick deviates from common offset')]
    put(c / 'live.tsv', shifted)
    p = c / 'frame-1.hex'
    pix = p.read_text().splitlines()
    pix[0] = f'{int(pix[0],16)^1:02x}'
    put(p, '\n'.join(pix) + '\n')
    rejected.append(must_reject('one PPU pixel changed'))
    put(a.out / 'result.json', json.dumps(dict(passed=True, comparator_only=True,
        new_RTL_execution=False, accepted_constant_offset=7, rejected=rejected,
        driver_sha256=sha(Path(__file__))), indent=2) + '\n')
    print('PASS comparator: constant+7 accepted; changed event and pixel rejected')

if __name__ == '__main__': main()
