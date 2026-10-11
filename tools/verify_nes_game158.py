# SPDX-License-Identifier: MIT
"""Verify frozen158 evidence and publication pins; does not rerun hardware models."""
from pathlib import Path
import argparse,json,zipfile
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
 m=json.loads((ROOT/'analysis/game158-verification.json').read_bytes());e=a.baseline/'nes-game158/evidence'
 assert sha(e/'manifest.json')==m['manifest_sha256'];files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['file_count']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for n in ['test','host','reuse']:assert json.loads((e/n/'result.json').read_bytes())['passed']
 timing=json.loads((e/'asm/timing150-phase.json').read_bytes());assert timing['passed'] and timing['implementation_budget_passed']
 test=json.loads((e/'test/result.json').read_bytes());positive=control=negative=0
 for run in test['runs']:
  assert len(run['rows'])==36
  for mode,disabled,fault,code,requests,responses in run['rows']:
   assert disabled==run['control']
   if disabled:assert fault==1 and code==2;control+=1
   elif mode==2:assert fault==1 and code==2;negative+=1
   else:assert fault==0 and code==0;positive+=1
 assert (positive,control,negative)==(72,108,36)
 assert sha(e/'test/game158_mapper_tb.sv')==sha(ROOT/'tests/nes-functional/game158_mapper_tb.sv')
 assert 'PASS158 mapper lookup 536 commits' in (e/'test/mapper.log').read_text()
 archive=e/'release/NES158-SMB3-CHR-PREVIEW.zip';assert sha(archive)==m['package']['zip_sha256']
 with zipfile.ZipFile(archive) as z:
  assert z.read('START-HERE.ko.md')==(ROOT/'docs/nes-game158-instructions.ko.md').read_bytes()
 assert not m['physical_test'] and not m['gameplay_passed'] and m['fit']['m9k']==56
 print('PASS158 frozen evidence/public pins/package:',len(files),'files;72 positive/108 control/36 retained-negative/536 mapper commits')
if __name__=='__main__':main()
