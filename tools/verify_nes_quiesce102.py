# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json
from nes_spi_boot import ROOT,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 m=json.loads((ROOT/'analysis/quiesce102-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256'];files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h==sha(e/'public-sources'/n),n
 for n,c in [('pins01',1024),('main02',18),('fat32-96-02',3)]:
  r=json.loads((e/n/'result.json').read_bytes());assert len(r['cases'])==c and all(x['exit']==0 for x in r['cases'])
  assert r['platform_sha256']==sha(e/'arm01/src/nes_diag_platform.c')
 for n in ['cs','clock','miso','reset','order','call','baseline']:
  d=e/('negative-'+n+'01');r=json.loads((d/'result.json').read_bytes());assert len(r['cases'])==1 and r['cases'][0]['exit']!=0
  assert sha(d/'executed-test102.py')==sha(e/'pins01/executed-test102.py')
 assert json.loads((e/'arm01/check102.json').read_bytes())==m['arm']
 assert sha(e/'arm01/src/obj-nes-100/firmware.stm')==m['arm']['firmware_sha256']
 assert not m['physical'] and not m['installable'] and not m['first_fault_to_quiesce_latency_proven']
 print('PASS102 frozen pins1024/main21/causal6/baseline1/ARM-MMIO16; physical open')
if __name__=='__main__':main()
