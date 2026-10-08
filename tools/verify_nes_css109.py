# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json
from nes_spi_boot import ROOT,sha
from nes_pair109 import verify

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 m=json.loads((ROOT/'analysis/css109-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h==sha(e/'public-sources'/n),n
 for name,count in m['runs'].items():
  r=json.loads((e/name/'result.json').read_bytes());assert len(r['cases'])==count
  assert sha(e/name/'executed-test109.py')==m['public_sources']['tools/test_nes_css109.py']
  for i,c in enumerate(r['cases']):
   assert sha(e/name/f'case-{i}.log')==c['log_sha256']
   assert c['exit']!=0 if r['mutation'] else c['exit']==0
 assert sha(e/'pair01/executed-prepare109.py')==m['public_sources']['tools/prepare_nes_pair109.py']
 assert sha(e/'pair-tests01/executed-test109.py')==m['public_sources']['tools/test_nes_pair109.py']
 assert verify(e/'pair01',m['pair_manifest_sha256'])['pair_identity_pass']
 t=json.loads((e/'pair-tests01/result.json').read_bytes());assert t['normal']==1 and t['rejected']==23
 assert not m['new_arm'] and not m['new_fpga'] and not m['physical'] and not m['installable']
 print('PASS109 integration38/control4/pair24; source links and frozen integrity; no physical approval')
if __name__=='__main__':main()
