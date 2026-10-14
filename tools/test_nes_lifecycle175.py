# SPDX-License-Identifier: MIT
"""Exercise deployed174 producer/consumer ownership under slow host consumption."""
from pathlib import Path
import argparse, json, os, re, shutil, subprocess
from nes_game147 import ROOT, sha

FILES = ['nes_native_planes165.sv', 'nes_native_compact_planes165.sv',
         'nes_native_raster_frame165.sv', 'nes_native_frame165.sv',
         'nes_native_fill165.sv', 'nes_native_export165.sv', 'nes_native_mailbox165.sv']

def main():
    p = argparse.ArgumentParser()
    for n in ['baseline', 'out', 'questa-bin']:
        p.add_argument('--'+n, type=Path, required=True)
    a = p.parse_args()
    assert os.environ.get('SALT_LICENSE_SERVER') == '18000@localhost'
    assert not a.out.exists() and str(a.out).isascii()
    pins = json.loads((ROOT/'analysis/errorzero174-verification.json').read_bytes())['sources']
    a.out.mkdir(parents=True)
    for n in FILES:
        assert sha(a.baseline/n) == pins[n], n
        shutil.copy2(a.baseline/n, a.out/n)
    tb = 'tests/nes-functional/native_lifecycle175_tb.sv'
    shutil.copy2(ROOT/tb, a.out/Path(tb).name)

    def run(exe, args, label, negative=False):
        with (a.out/(label+'.log')).open('wb') as f:
            r = subprocess.run([str(a.questa_bin/(exe+'.exe')), *args], cwd=a.out,
                               stdout=f, stderr=subprocess.STDOUT, timeout=1800)
        s = (a.out/(label+'.log')).read_text(errors='replace')
        if negative:
            assert 'lifecycle watchdog commits=1 owned=1' in s, s[-4000:]
            assert 'PASS LIFECYCLE175' not in s
        else:
            assert r.returncode == 0 and not re.search(r'\*\* (Error|Fatal):', s), s[-4000:]
        return s

    run('vlib', ['work'], 'vlib')
    run('vlog', ['-sv', *FILES, Path(tb).name], 'vlog')
    s = run('vsim', ['-c', 'work.native_lifecycle175_tb', '-do',
                    'onerror {quit -code 1}; run -all; quit -f'], 'normal')
    m = re.search(r'PASS LIFECYCLE175 commits=(\d+) begins=(\d+) ends=(\d+) rejects=(\d+) releases=(\d+) held_frames=(\d+) frames=(\d+)', s)
    assert m
    run('vsim', ['-c', 'work.native_lifecycle175_tb', '-gDROP_RELEASE=1', '-do',
                 'onerror {quit -code 1}; run -all; quit -f'], 'negative', True)
    result = dict(passed=True, counts=dict(zip(['commits', 'begins', 'ends', 'rejects', 'releases', 'held_frames', 'frames'], map(int, m.groups()))),
                  dropped_release_negative_detected=True, sources={n: sha(a.out/n) for n in FILES},
                  public_sources={n: sha(ROOT/n) for n in [tb, 'tools/test_nes_lifecycle175.py']},
                  logs={n: sha(a.out/n) for n in ['vlib.log', 'vlog.log', 'normal.log', 'negative.log']},
                  scope='Exact deployed174 collectors/fill/exporter/mailboxes. Synthetic224-row PPU events at nominal frame cadence; host170ms then40ms stalls and1ms PREPARED delay. Modeled ROM bytes/host, no actual game, physical SPI, SNES display or FPS proof.')
    (a.out/'result.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
    print(m[0], flush=True)

if __name__ == '__main__':
    main()
