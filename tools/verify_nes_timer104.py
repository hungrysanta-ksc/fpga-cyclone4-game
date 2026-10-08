# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json
from nes_spi_boot import ROOT,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 m=json.loads((ROOT/'analysis/timer104-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h==sha(e/'public-sources'/n),n
 suites=[('units04',60),('main02',20),('fat32-96-02',3),('timer-ticks-01',1),('timer-frozen-01',1)]
 suites += [('negative-'+n+'-03',1) for n in ['baseline','timer-bound','timer-cleanup','card-state','reset-invert','cic-threshold']]
 for n,c in suites:
  d=e/n;r=json.loads((d/'result.json').read_bytes());assert len(r['cases'])==c
  for i,case in enumerate(r['cases']):
   assert bool(case['exit'])==n.startswith('negative-')
   assert sha(d/f'case-{i}.log')==case['log_sha256']
  assert sha(d/'executed-test104.py')==m['public_sources']['tools/test_nes_timer104.py']
  for f in ['peripherals104_model.inc','peripherals104_cases.inc']:assert sha(d/f)==m['public_sources']['tests/nes-functional/'+f]
 assert sha(e/'arm01/executed-prepare104.py')==m['public_sources']['tools/prepare_nes_timer104.py']
 assert json.loads((e/'arm01/check104.json').read_bytes())==m['arm']
 assert sha(e/'arm01/src/obj-nes-100/firmware.stm')==m['arm']['firmware_sha256']
 assert not m['physical'] and not m['installable'] and not m['exhaustive_irq_proven']
 print('PASS104 frozen units60/main23/timer-stall2/controls6/ARM; physical and exhaustive IRQ timing not proven')
if __name__=='__main__':main()
