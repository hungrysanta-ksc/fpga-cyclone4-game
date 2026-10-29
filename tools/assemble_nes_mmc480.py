# SPDX-License-Identifier: MIT
"""Assemble exact fitted479 sources without repeating MAP/FIT or changing ROM."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from nes_cf68_pair_preflight import encode, decode

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--board', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
r = json.loads((ROOT/'analysis/mmc479-verification.json').read_text())
for n, h in r['whole_board_inputs'].items():
    assert sha(a.board/n) == h, n
a.out.mkdir(parents=True, exist_ok=False)
fit_hash = sha(a.board/'output_files/board.fit.rpt')
bin = Path('C:/altera_lite/25.1std/quartus/bin64')
for label, args in [('asm', ['quartus_asm.exe', 'board']), ('cpf', ['quartus_cpf.exe', '-c', 'output_files/board.sof', 'output_files/board.rbf'])]:
    with (a.out/(label+'.log')).open('wb') as log:
        q = subprocess.run([str(bin/args[0]), *args[1:]], cwd=a.board, stdout=log, stderr=subprocess.STDOUT, timeout=180, creationflags=subprocess.CREATE_NO_WINDOW)
    assert q.returncode == 0, (a.out/(label+'.log')).read_text(errors='replace')[-4000:]
assert sha(a.board/'output_files/board.fit.rpt') == fit_hash
raw = (a.board/'output_files/board.rbf').read_bytes()
packed = encode(raw)
assert decode(packed) == raw
(a.out/'fpga_mmc480.bi3').write_bytes(packed)
result = {'passed': True, 'scope': __doc__, 'unchanged_FIT_report': fit_hash, 'source_inputs': r['whole_board_inputs'], 'RBF_bytes': len(raw), 'RBF_SHA256': sha(a.board/'output_files/board.rbf'), 'BI3_bytes': len(packed), 'BI3_SHA256': sha(a.out/'fpga_mmc480.bi3'), 'hardware': False}
(a.out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({'passed': True, 'BI3_bytes': len(packed), 'hardware': False}))
