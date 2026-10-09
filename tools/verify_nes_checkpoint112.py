# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,zipfile
from nes_spi_boot import ROOT,sha
from nes_pair109 import expected,digest
from verify_nes_trial111 import ROLES
from release_nes_checkpoint112 import FIRMWARE

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence
 meta=json.loads((ROOT/'analysis/checkpoint112-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];assert len(pins)==meta['archived_files']
 for n,h in pins.items():assert sha(e/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h==sha(e/'public-sources'/n),n
 arm=json.loads((e/'arm-check02/result.json').read_bytes());assert arm==meta['arm']
 for n,h in json.loads((e/'host03/result.json').read_bytes())['production_sources'].items():assert sha(e/'arm02/src'/n)==h,n
 for d,count in [('host03',24),('budget01',1),('readback01',1),('readback96-01',1)]:
  data=json.loads((e/d/'result.json').read_bytes());assert len(data['cases'])==count
  for i,c in enumerate(data['cases']):assert not c['exit'] and sha(e/d/f'case-{i}.log')==c['log_sha256']
 for d in ['readback01','readback96-01']:
  data=(e/d/'case-0-file.txt').read_bytes();assert len(data)%512==0 and b'stage=MENU_PREPARED' in data
 zpath=e/'release01/NES112-PROGRESS-LOG-and-RESTORE044.zip';assert sha(zpath)==meta['release']['zip_sha256']
 with zipfile.ZipFile(zpath) as z:
  assert set(z.namelist())==set(ROLES)|{'manifest.json','START-HERE.ko.md','decision112.json'} and len(z.namelist())==12
  m=json.loads(z.read('manifest.json'))
  for n,v in m['files'].items():assert len(z.read(n))==v['bytes'] and digest(z.read(n))==v['sha256']
  for n,role in ROLES.items():
   h=FIRMWARE if role=='arm108.stm' else expected()[role]['sha256'];assert digest(z.read(n))==h,n
  assert z.read('START-HERE.ko.md')==(ROOT/'docs/nes-checkpoint112-instructions.ko.md').read_bytes()
  d=json.loads(z.read('decision112.json'));assert d['hardware_trial_approved'] and d['fixture_kib']==80 and d['attempts']==1
  assert not any(d[k] for k in ['full_nes_installable','start_enabled','electrical_signoff','common_cause_8us_proven'])
 print('PASS112 evidence/source links/host-ARM identity/actual FatFS log readback/exact release roles; physical pending')
if __name__=='__main__':main()
