# SPDX-License-Identifier: MIT
"""Pack the already assembled482 RBF after checking the full source closure."""
import argparse
import hashlib
import json
from pathlib import Path
from nes_cf68_pair_preflight import encode, decode

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
p = argparse.ArgumentParser(description=__doc__)
for n in ['candidate', 'board', 'out']:
    p.add_argument('--'+n, type=Path, required=True)
a = p.parse_args()
r = json.loads((a.candidate/'preparation.json').read_text(encoding='utf8'))
for n, h in r['board_inputs'].items():
    assert sha(a.board/n) == h, n
assert 'Successful' in (a.board/'output_files/board.fit.summary').read_text(encoding='utf8')
raw = (a.board/'output_files/board.rbf').read_bytes()
packed = encode(raw)
assert decode(packed) == raw
a.out.mkdir(parents=True, exist_ok=False)
(a.out/'fpga_mmc482.bi3').write_bytes(packed)
result = {'passed': True, 'scope': __doc__, 'source_inputs': r['board_inputs'],
          'RBF_SHA256': sha(a.board/'output_files/board.rbf'),
          'BI3_SHA256': sha(a.out/'fpga_mmc482.bi3'), 'BI3_bytes': len(packed),
          'fit_report_SHA256': sha(a.board/'output_files/board.fit.rpt')}
(a.out/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
print(json.dumps({'packed': True, 'BI3_bytes': len(packed)}))
