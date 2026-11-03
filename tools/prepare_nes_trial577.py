# SPDX-License-Identifier: MIT
"""Copy the measured MMC558 ARM tree and change only three same-width labels."""
import argparse,json,shutil
from pathlib import Path
from nes_raw506 import sha
from package_nes_window516 import LABELS
p=argparse.ArgumentParser()
p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();root=Path(__file__).resolve().parents[1]
expected=json.loads((root/'analysis/trial558-package.json').read_text())['firmware_SHA256']
assert sha(a.base/'src/obj-nes-100/firmware.stm')==expected
assert not a.out.exists()
shutil.copytree(a.base,a.out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
for n in LABELS:
 f=a.out/'src'/n;s=f.read_text();assert '558' in s
 f.write_text(s.replace('558','577'),newline='\n')
print(a.out)
