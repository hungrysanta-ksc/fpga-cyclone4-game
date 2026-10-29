# SPDX-License-Identifier: MIT
"""Rename only479 menu/checkpoint trial paths to480; preserve profile79/logic."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
p = argparse.ArgumentParser(description=__doc__)
for n in ['candidate', 'out']:
    p.add_argument('--'+n, type=Path, required=True)
a = p.parse_args()
r = json.loads((ROOT/'analysis/mmc479-verification.json').read_text())
a.out.mkdir(parents=True, exist_ok=False)
for n, h in r['ARM_patch'].items():
    assert sha(a.candidate/n) == h, n
    shutil.copyfile(a.candidate/n, a.out/n)
for n in ['nes_menu_diagnostic.c', 'nes_checkpoint112.c']:
    f = a.out/n
    s = f.read_text().replace('mmc479', 'mmc480').replace('MMC479', 'MMC480').replace('NES MMC3 479.nh1', 'NES MMC3 480.nh1')
    f.write_text(s, newline='\n')
result = {'baseline479': r['ARM_patch'], 'generated': {f.name: sha(f) for f in a.out.iterdir()}, 'scope': __doc__, 'logic_and_profile_unchanged': True}
(a.out/'preparation480.json').write_text(json.dumps(result, indent=2)+'\n')
print('480 trial labels prepared; no package or hardware approval')
