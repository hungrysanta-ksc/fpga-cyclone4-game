# SPDX-License-Identifier: MIT
"""Verify frozen159 evidence, causal controls, publication pins and package."""
from pathlib import Path
import argparse,json,zipfile
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
 m=json.loads((ROOT/'analysis/game159-verification.json').read_bytes());e=a.baseline/'nes-game159/evidence'
 assert sha(e/'manifest.json')==m['manifest_sha256'];files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['file_count']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for n in ['test','host','reuse']:assert json.loads((e/n/'result.json').read_bytes())['passed']
 timing=json.loads((e/'asm/timing150-phase.json').read_bytes());assert timing['passed'] and not timing['implementation_budget_passed']
 assert timing['same_clock_setup_ns']==0.095 and timing['implementation_budget_setup_ns']==-0.036
 assert (e/'asm/board.sdc').read_bytes()==(a.baseline/'nes-game158/evidence/asm/board.sdc').read_bytes()
 test=json.loads((e/'test/result.json').read_bytes());positive=control=faults=0
 for run in test['runs']:
  assert len(run['rows'])==13 and [row[0] for row in run['rows']]==list(range(-1,12))
  log=e/'test'/('phase-'+str(run['phase_ns'])+'-control-'+str(run['control'])+'.log')
  assert sha(log)==run['log_sha256'];s=log.read_text()
  assert 'ELIGIBILITY159 48' in s and 'READ159 source=0 samples=6' in s and 'READ159 source=1 samples=6' in s
  for offset,disabled,failed,error,checked,requests,write_reads in run['rows']:
   assert disabled==run['control']
   if disabled:
    assert write_reads==1;control+=1;faults+=failed
    if offset==-1:assert failed==1 and error==2
   else:assert failed==0 and error==0 and checked>=2 and write_reads==0;positive+=1
 assert (positive,control,faults)==(39,39,18),(positive,control,faults)
 assert sha(e/'test/game159_eligibility_tb.sv')==sha(ROOT/'tests/nes-functional/game159_eligibility_tb.sv')
 archive=e/'release/NES159-SMB3-WRITE-GUARD.zip';assert sha(archive)==m['package']['zip_sha256']
 with zipfile.ZipFile(archive) as z:assert z.read('START-HERE.ko.md')==(ROOT/'docs/nes-game159-instructions.ko.md').read_bytes()
 assert not m['physical_test'] and not m['gameplay_passed'] and m['fit']['m9k']==56
 print('PASS159 frozen evidence/public pins/package:',len(files),'files;39 positive/39 unnecessary-read controls/18 deadline failures')
if __name__=='__main__':main()
