# SPDX-License-Identifier: MIT
"""Current482 versus484 resident allocator: exact state, slots, writes and faults.

Reuse221 directed collisions,180 synthetic frames, generation wrap, cold/epoch,
bank/commit identity failures, exhaustion and writer failure/abort. This is a
host differential test, not a new SPI/RTL/65816 STOP or timing proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sha = lambda q: hashlib.sha256(q.read_bytes()).hexdigest()
p = argparse.ArgumentParser(description=__doc__)
for n in ['base', 'arm', 'preparation', 'out']:
    p.add_argument('--'+n, required=True, type=Path)
a = p.parse_args()
prep = json.loads(a.preparation.read_text(encoding='utf8'))
for n, h in prep['baseline_sources'].items():
    assert sha(a.base/n) == h
    assert sha(a.arm/n) == prep['patch_sources'].get(n, h)
a.out = a.out.resolve()
a.out.mkdir(parents=True, exist_ok=False)
inputs = {}
for q in a.arm.glob('nes_*.h'):
    shutil.copyfile(q, a.out/q.name)
    inputs[q.name] = sha(q)
shutil.copyfile(a.arm/'nes_resident211.c', a.out/'nes_resident211.c')
s = (a.base/'nes_resident211.c').read_text(encoding='utf8')
s = s.replace('nes_resident211_', 'baseline_').replace('baseline_write_fn', 'nes_resident211_write_fn')
(a.out/'baseline.c').write_text(s, encoding='utf8', newline='\n')
q = ROOT/'tests/nes-functional/index221_host.c'
s = q.read_text(encoding='utf8')
assert s.count('offsetof(struct nes_resident211,index_head)') == 1
s = s.replace('offsetof(struct nes_resident211,index_head)', 'sizeof state[0]')
# Both versions already have the same index. Retain all functional assertions,
# remove only221's old linear-versus-indexed performance assertion.
check = ' assert(index221_probes+index221_rebuild<baseline_probes);'
assert s.count(check) == 1
s = s.replace(check, '')
(a.out/'index221_host.c').write_text(s, encoding='utf8', newline='\n')
inputs['original_index221_host.c'] = sha(q)
gcc = Path('C:/altera_lite/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
env = os.environ.copy()
env['PATH'] = str(gcc.parent)+os.pathsep+env.get('PATH', '')
for args, name in [([gcc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2', 'index221_host.c',
                    'nes_resident211.c', 'baseline.c', '-o', 'guard.exe'], 'build'),
                   ([a.out/'guard.exe'], 'guards')]:
    with (a.out/(name+'.log')).open('wb') as log:
        r = subprocess.run(list(map(str, args)), cwd=a.out, env=env, stdout=log, stderr=subprocess.STDOUT,
                           timeout=180, creationflags=subprocess.CREATE_NO_WINDOW)
    text = (a.out/(name+'.log')).read_text(encoding='utf8', errors='replace')
    assert r.returncode == 0, text[-6000:]
assert 'PASS INDEX221' in text
r = {'passed': True, 'scope': __doc__, 'output': text, 'inputs': inputs,
     'preparation_SHA256': sha(a.preparation),
     'logs': {n: sha(a.out/n) for n in ['build.log', 'guards.log']},
     'full_resident_index_state_compared': True, 'physical': False, 'new_RTL': False}
(a.out/'result.json').write_text(json.dumps(r, indent=2)+'\n', encoding='utf8')
print(text)
