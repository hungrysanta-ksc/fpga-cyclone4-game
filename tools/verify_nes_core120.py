# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,hashlib
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 root=Path(__file__).resolve().parents[1];meta=json.loads((root/'analysis/core120-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 m=json.loads((e/'manifest.json').read_bytes())
 for n,h in m['files'].items():assert sha(e/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(root/n)==h,n
 core=json.loads((e/'core04/result.json').read_bytes());unit=json.loads((e/'unit01/result.json').read_bytes())
 assert core['passed'] and len(core['cases'])==8 and unit['passed'] and len(unit['cases'])==16 and unit['negative110_rejected']
 for r in core['cases']:
  log=e/f"core04/read{r['read_cycles']}-access{r['access_ns']}/{r['case']}/simulation.log"
  assert sha(log)==r['log_sha256']
  if (r['read_cycles'],r['access_ns'])==(3,70):assert r['outcome']=='rejected' and r['reason']=='CPU ROM byte mismatch'
  else:assert r['outcome']=='pass' and r['responses']>=8192 and r['cpu_samples']>=128 and r['ppu_samples']>=128
 assert sum(c['completed'] for c in unit['cases'])==8400
 h=json.loads((e/'hardware119/interpretation.json').read_bytes())
 assert h['report']['verified']=='1' and h['report']['compared_bytes']=='81920' and h['user_report']['restore044'] is True
 print('PASS120 hardware119 + eight core conditions +16phase/110ns control + sources/evidence')
if __name__=='__main__':main()
