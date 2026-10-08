# SPDX-License-Identifier: MIT
"""Verify source pins and frozen observation-only evidence, not hardware."""
from pathlib import Path
import argparse,json,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence.resolve()
 m=json.loads((ROOT/'analysis/clock-observation087-verification.json').read_text())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_text())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():
  f=(e/n).resolve();assert f.is_relative_to(e) and sha(f)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 read=lambda n:json.loads((e/n).read_text())
 fit=read('fit01/result.json');short=read('short04/result.json');audit=read('audit01/result.json')
 assert min(fit['summary_slacks'])==0.187 and len(fit['summary_slacks'])==18
 for n,h in short['sources'].items():
  assert h==fit['sources'][n]==sha(e/'normal02'/n)==sha(e/'short04'/n)==sha(e/'fit01'/n),n
 log=(e/'normal02/case0.log').read_text(errors='replace')
 assert 'PASS OBSERVATION087 count=1250000 commands=254 coherent=1 both_halt_parked=1' in log
 assert '** Fatal:' not in log
 # This next full-window case FAILED: record the exact rounded stimulus cause,
 # never promote the overall normal02 run to a three-frequency success.
 log=(e/'normal02/case1.log').read_text(errors='replace')
 assert 'FREQUENCY_WINDOW_MISMATCH count=1375017 expected=1375000' in log
 assert len(short['cases'])==3 and short['window_cycles']==80000
 for i,c in enumerate(short['cases']):
  assert abs(c['count']-c['expected_count'])<=2
  log=(e/'short04'/f'case{i}.log').read_text(errors='replace')
  assert 'PASS ABSENT_AND_RECOVERED_WINDOWS087' in log and '** Fatal:' not in log
 assert len(audit['crossings'])==6 and len(audit['constant_high'])==10 and len(audit['output_disabled'])==32
 for name in ['same-clock','live-snapshot','memory-enable']:
  folder=name+('02' if name=='same-clock' else '01')
  r=read(folder+'/result.json');assert r['mutation']==name and r['window_cycles']==80000
  log=(e/folder/'case0.log').read_text(errors='replace')
  assert '** Fatal:' in log and r['cases'][0]['expected_failure'] in log
 assert not m['installable'] and not m['hardware_execution'] and not m['cf86_requalified']
 print('PASS CF87: full20MHz case +3 short cases +3 causal controls; same2 fit RTL;18 STA summaries;6 routed crossings;10/32 parked pins. No physical/MCU/package approval.')

if __name__=='__main__':main()
