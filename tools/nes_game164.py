# SPDX-License-Identifier: MIT
"""Prepare MCU164 and routed163 for the vblank-only client ROM update."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha

def prepare(baseline,out,client=None,arm=False):
 e=baseline/'nes-game163/evidence';m=json.loads((ROOT/'analysis/game163-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256'];pins=json.loads((e/'manifest.json').read_bytes())['files']
 assert not out.exists() and str(out).isascii()
 section='arm' if arm else 'asm'
 names=list(json.loads((e/'arm/preparation163.json').read_bytes())['copied']) if arm else [n[4:] for n in pins if n.startswith('asm/')]
 out.mkdir(parents=True);inputs={}
 for n in names:
  src=e/section/n;assert sha(src)==pins[section+'/'+n],n
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);inputs[n]=sha(src)
 def edit(n,a,b,count=None):
  p=out/n;s=p.read_text();assert a in s,n
  if count is not None:assert s.count(a)==count,(n,s.count(a))
  p.write_text(s.replace(a,b),encoding='utf8',newline='\n')
 if arm:
  for n in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:edit('src/'+n,'163','164')
 else:
  assert client is not None
  r=json.loads((client/'result.json').read_bytes());assert r['passed']
  shutil.copy2(client/'client/game-program.hex',out/'game-program.hex')
 changed={n:sha(out/n) for n,h in inputs.items() if sha(out/n)!=h}
 if not arm:assert set(changed)=={'game-program.hex'}
 # Deliberately retain the exact162 RTL identity6B/E5, not a new/widened ID set.
 # Firmware164 filenames identify the package; A9 is the reused SPC status,
 # not a unique client-version token. Always install firmware and FPGA together.
 (out/'preparation164.json').write_text(json.dumps(dict(copied=inputs,changed=changed,added={},ids=['6B','E5'],client='164',rtl_reused='162',physical=False),indent=2)+'\n')
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--client',type=Path);p.add_argument('--arm',action='store_true');a=p.parse_args();prepare(a.baseline,a.out,a.client,a.arm)
