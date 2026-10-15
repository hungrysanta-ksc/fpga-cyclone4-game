# SPDX-License-Identifier: MIT
"""Bounded local producer -> immutable chunks -> raw SNES read bus RTL.

Replays actual archived C request bytes, NOT a new CPU/PPU/mapper integration.
Preserves full simulation logs. Requires the approved FLOAT wrapper.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, subprocess

ROOT = Path(__file__).resolve().parents[1]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    for key in ('out', 'questa-bin'):
        ap.add_argument('--'+key, type=Path, required=True)
    a = ap.parse_args()
    assert os.environ.get('SALT_LICENSE_SERVER') == '18000@localhost'
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=False)
    pins = {}
    sources = ['src/nes/rtl/nes_bulk_aperture188.sv',
               'src/nes/diagnostic/nes_domain_reset124.sv',
               'tests/nes-functional/bulk_aperture188_tb.sv']
    for name in sources:
        p = ROOT/name
        shutil.copyfile(p, a.out/p.name)
        pins[name] = sha(p)
    board = ROOT.parent/'probes/nes-window184-coupled/evidence/route02'
    for name in ('nes_sink_bus165.sv', 'sink-program.hex'):
        shutil.copyfile(board/name, a.out/name)
        pins[(board/name).relative_to(ROOT.parent).as_posix()] = sha(board/name)
    fixtures = ROOT.parent/'probes/nes-copy186/evidence/coupled03/inherit'
    frames = {}
    for p in sorted(fixtures.glob('req-*.bin')):
        data = p.read_bytes()
        assert len(data) == 16+int.from_bytes(data[12:14], 'little')
        gen = int.from_bytes(data[8:10], 'little')
        frames.setdefault(gen, bytearray()).extend(data)
        pins[p.relative_to(ROOT.parent).as_posix()] = sha(p)
    assert len(frames) == 7
    rows = [str(len(frames))]
    for gen, data in frames.items():
        name = f'stream-{gen}.hex'
        (a.out/name).write_text(''.join(f'{v:02x}\n' for v in data), encoding='ascii')
        rows.append(f'{name} {len(data)} {gen*4096}')
    (a.out/'streams.txt').write_text('\n'.join(rows)+'\n', encoding='ascii')
    def run(exe, args, label):
        with (a.out/(label+'.log')).open('wb') as log:
            q = subprocess.run([str(a.questa_bin/(exe+'.exe')), *args], cwd=a.out,
                               stdout=log, stderr=subprocess.STDOUT, timeout=120,
                               creationflags=subprocess.CREATE_NO_WINDOW)
        text = (a.out/(label+'.log')).read_text(errors='replace')
        assert q.returncode == 0 and not re.search(r'\*\* (Error|Fatal):', text), text[-6000:]
        return text
    run('vlib', ['work'], 'vlib')
    run('vlog', ['-sv', 'nes_sink_bus165.sv', *[Path(n).name for n in sources]], 'vlog')
    cases = []
    for phase in (0, 3.5):
        text = run('vsim', ['-c', 'work.bulk_aperture188_tb', f'-gPHASE={phase}',
                           '-do', 'onerror {quit -code 1}; run -all; quit -f'], f'phase-{phase}')
        match = re.search(r'PASS BULK188 checks=(\d+) reads=(\d+) streams=(\d+)', text)
        assert match, text[-6000:]
        cases.append(dict(phase_ns=phase, checks=int(match[1]), bytes_read=int(match[2]), streams=int(match[3])))
    result = dict(passed=True, cases=cases, source_pins=pins,
                  streams={str(k):len(v) for k,v in frames.items()},
                  payload_storage_bytes=4096, nominal_m9k_estimate=4,
                  scope=__doc__, producer_clock='host clk; NES-domain CDC not implemented',
                  physical_timing=False, actual_cpu_dma=False, fit=False,
                  stable_pattern_cache=False, hardware_package=False)
    (a.out/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='source_pins'}, indent=2))

if __name__ == '__main__':
    main()
