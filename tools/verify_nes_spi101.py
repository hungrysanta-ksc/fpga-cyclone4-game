# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json
from nes_spi_boot import ROOT,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 m=json.loads((ROOT/'analysis/spi101-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h==sha(e/'public-sources'/n),n
 phase=json.loads((e/'phase04/result.json').read_bytes());assert len(phase['cases'])==336 and all(x['exit']==0 for x in phase['cases'])
 for n,c in [('unit01',13),('main02',18),('fat32-96-01',3)]:
  r=json.loads((e/n/'result.json').read_bytes());assert len(r['cases'])==c and all(x['exit']==0 for x in r['cases'])
  assert (e/n/'production-stm32f4xx-spi.c').read_text()==(e/'arm02/src/stm32f4xx/spi.c').read_text()
 for n in ['sync','exchange','reverse','fault','baseline-sync','baseline-exchange']:
  r=json.loads((e/('negative-'+n+'02')/'result.json').read_bytes());assert len(r['cases'])==1 and r['cases'][0]['exit']!=0
  assert sha(e/('negative-'+n+'02')/'executed-test101.py')==sha(e/'phase04/executed-test101.py')
 arm=json.loads((e/'arm02/check101.json').read_bytes());assert arm==m['arm']
 assert sha(e/'arm02/src/obj-nes-100/firmware.stm')==arm['firmware_sha256']
 assert m['installable'] is False and m['inflight_spi_abort_proven'] is False
 print('PASS101 frozen phase336/lower34/causal4/baseline2/ARM; physical and abort open')
if __name__=='__main__':main()
