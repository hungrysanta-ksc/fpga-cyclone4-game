# SPDX-License-Identifier: MIT
"""Verify frozen160 selected results and publication/package hashes, no rebuild."""
from pathlib import Path
import argparse,json,zipfile
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
 m=json.loads((ROOT/'analysis/game160-verification.json').read_bytes());e=a.baseline/'nes-game160/evidence'
 assert sha(e/'manifest.json')==m['manifest_sha256'];files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['file_count']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for n in ['test','host','reuse']:assert json.loads((e/n/'result.json').read_bytes())['passed']
 timing=json.loads((e/'asm/timing150-phase.json').read_bytes());assert timing['passed']
 assert (e/'asm/nominal156.sdc').read_bytes()==(a.baseline/'nes-game159/evidence/asm/nominal156.sdc').read_bytes()
 t=json.loads((e/'test/result.json').read_bytes());assert len(t['runs'])==24 and len(t['regression159'])==6
 assert len({(r['phase_ns'],r['dot'],r['latch'],r['control']) for r in t['runs']})==24
 for r in t['runs']:
  assert r['failed']==r['control'] and r['error']==(2 if r['control'] else 0)
  if not r['control']:assert r['checked']>=1
  log=e/'test'/f"phase-{r['phase_ns']}-dot-{r['dot']}-latch-{r['latch']}-control-{r['control']}.log";assert sha(log)==r['log_sha256']
 assert sha(e/'test/game160_transition_tb.sv')==sha(ROOT/'tests/nes-functional/game160_transition_tb.sv')
 assert sha(ROOT/'tests/nes-functional/game159_eligibility_tb.sv')==t['regression159_original_sha256']
 assert '$isunknown' in (e/'test/game160_transition_tb.sv').read_text()
 for n,h in t['sources'].items():assert sha((e/'test' if n.startswith('game') else e/'asm')/n)==h,n
 archive=e/'release/NES160-SMB3-RENDER-RESTART.zip';assert sha(archive)==m['package']['zip_sha256']
 with zipfile.ZipFile(archive) as z:assert z.read('START-HERE.ko.md')==(ROOT/'docs/nes-game160-instructions.ko.md').read_bytes()
 assert not m['physical_test'] and not m['gameplay_passed'] and m['fit']['m9k']==56
 print('PASS160 frozen evidence/public pins/package:',len(files),'files;12 restart/12 old-control faults;159 regression retained')
if __name__=='__main__':main()
