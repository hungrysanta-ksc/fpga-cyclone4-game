# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json
from nes_spi_boot import ROOT,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 m=json.loads((ROOT/'analysis/observer103-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h==sha(e/'public-sources'/n),n
 for n,c in [('unit03',17),('main04',18),('fat32-96-02',3),('stall02',16)]:
  r=json.loads((e/n/'result.json').read_bytes());assert len(r['cases'])==c
  for case in r['cases']:
   assert case['exit']==0 and case['last'].startswith('PASS103')
  driver='test_nes_observer103.py' if n=='unit03' else 'test_nes_observer103_main.py'
  executed='executed-test103.py' if n=='unit03' else 'executed-main103.py'
  assert sha(e/n/executed)==m['public_sources']['tools/'+driver]
 for n in ['baseline','observer','uart','flush','scope','order']:
  d=e/('control-'+n+'-02');r=json.loads((d/'result.json').read_bytes());assert len(r['cases'])==1 and r['cases'][0]['exit']!=0
  assert sha(d/'executed-test103.py')==m['public_sources']['tools/test_nes_observer103.py']
 assert json.loads((e/'arm01/check103-final.json').read_bytes())==m['arm']
 assert sha(e/'arm01/src/obj-nes-100/firmware.stm')==m['arm']['firmware_sha256']
 assert not m['physical'] and not m['installable'] and not m['physical_latency_proven']
 print('PASS103 frozen unit17/main21/UART-stall16/controls6/ARM-MMIO16; physical and timer/CIC integration open')
if __name__=='__main__':main()
