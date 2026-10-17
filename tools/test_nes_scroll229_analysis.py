# SPDX-License-Identifier: MIT
"""Reject corrupted/unsupported evidence, without changing the selected capture."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, sys

from analyze_nes_scroll229 import FETCH, WRITE


def main():
    p = argparse.ArgumentParser()
    for n in ('capture', 'control', 'rom', 'out'):
        p.add_argument('--'+n, type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    sandbox = a.out/'fault-capture'
    shutil.copytree(a.capture, sandbox, ignore=shutil.ignore_patterns('*.nes'))
    fetch = (sandbox/'ppu-fetch.bin').read_bytes()
    writes = (sandbox/'writes.bin').read_bytes()
    results = []

    def reject(name, expected):
        command = [sys.executable, '-B', '-X', 'utf8', str(Path(__file__).with_name('analyze_nes_scroll229.py')),
                   '--capture', str(sandbox), '--control', str(a.control), '--rom', str(a.rom),
                   '--out', str(a.out/(name+'.json'))]
        run = subprocess.run(command, capture_output=True)
        output = run.stdout+run.stderr
        (a.out/(name+'.log')).write_bytes(output)
        assert run.returncode != 0 and expected.encode() in output, (name, output[-2000:])
        assert not (a.out/(name+'.json')).exists(), 'Failed evidence was published as a result'
        results.append(dict(case=name, rejected=True, reason=expected))

    (sandbox/'ppu-fetch.bin').write_bytes(fetch[:-1])
    reject('truncated-fetch', 'truncated record')
    row = list(FETCH.unpack_from(fetch)); row[4] ^= 1
    (sandbox/'ppu-fetch.bin').write_bytes(FETCH.pack(*row)+fetch[FETCH.size:])
    reject('wrong-chr-value', 'captured CHR byte differs')
    (sandbox/'ppu-fetch.bin').write_bytes(fetch)
    damaged = bytearray()
    for row in WRITE.iter_unpack(writes):
        row = list(row)
        if row[0] == 0 and row[4] == 0x2001:
            row[4] = 0x2000
        damaged.extend(WRITE.pack(*row))
    (sandbox/'writes.bin').write_bytes(damaged)
    reject('missing-mask-witness', 'missing fetch without observed mask change')
    # Keep the mutated evidence and failure logs for inspection, never alter
    # or silently replace the original selected run.
    assert (a.capture/'ppu-fetch.bin').read_bytes() == fetch
    assert (a.capture/'writes.bin').read_bytes() == writes
    result = dict(passed=True, cases=results, selected_capture_unchanged=True,
                  analyzer_sha256=hashlib.sha256(Path(__file__).with_name('analyze_nes_scroll229.py').read_bytes()).hexdigest())
    (a.out/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
