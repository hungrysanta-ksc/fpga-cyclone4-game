# SPDX-License-Identifier: MIT
"""Resolve the documented length165 runner name collision without rewriting evidence."""
import hashlib
from nes_game147 import ROOT,sha

OLD='tools/test_nes_length165.py'
NEW='tools/test_nes_balancedlength165.py'
CHECKERS={f'tools/check_nes_{n}165.py' for n in ['length','lengthkeep','commandguard']}

def canonical_pins(pins):
 result={}
 for name,expected in pins.items():
  target=NEW if name==OLD else name
  actual=sha(ROOT/target)
  if actual!=expected:
   assert name==OLD or name in CHECKERS,name
   raw=(ROOT/target).read_bytes()
   raw=raw.replace(b'test_nes_balancedlength165',b'test_nes_length165')
   raw=raw.replace(b'from nes_lengthpublication165 import canonical_pins\n',b'')
   raw=raw.replace(b' public=canonical_pins(public)\n',b'')
   assert hashlib.sha256(raw).hexdigest()==expected,('publication-only normalization',name)
  result[target]=actual
 result['tools/nes_lengthpublication165.py']=sha(ROOT/'tools/nes_lengthpublication165.py')
 return result
