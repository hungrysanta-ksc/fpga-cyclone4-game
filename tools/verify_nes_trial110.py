# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,zipfile
from nes_spi_boot import ROOT,sha
from stage_nes_trial110 import FILES,digest

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 meta=json.loads((ROOT/'analysis/trial110-verification.json').read_bytes());assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];assert len(pins)==meta['archived_files']
 for n,h in pins.items():assert sha(e/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h==sha(e/'public-sources'/n),n
 assert sha(e/'stage02/executed-stage110.py')==meta['public_sources']['tools/stage_nes_trial110.py']
 r=json.loads((e/'stage02/result.json').read_bytes());assert r['members']==13 and r['file_roles']==9
 zpath=e/'stage02/NES110-REVIEW-DO-NOT-INSTALL.zip';assert sha(zpath)==r['zip_sha256']
 pair=json.loads((ROOT/'analysis/css108-verification.json').read_bytes())
 with zipfile.ZipFile(zpath) as z:
  m=json.loads(z.read('manifest.json'));assert set(z.namelist())==set(m['files'])|{'manifest.json'}
  for n,v in m['files'].items():assert len(z.read(n))==v['bytes'] and digest(z.read(n))==v['sha256']
  assert set(FILES)<=set(m['files'])
  assert digest(z.read('review-only/trial/sd2snes/firmware.stm'))==pair['arm']['firmware_sha256']
  d=json.loads(z.read('review-only/nes-trial110-decision.json'));assert d['selection']=='pending'
  assert z.read('review-only/nes-trial110-review.ko.md')==(ROOT/'docs/nes-trial110-review.ko.md').read_bytes()
  assert not d['hardware_trial_approved'] and not d['installable'] and not d['user_limited_trial_consent']
 assert not meta['new_arm'] and not meta['physical'] and not meta['installable']
 print('PASS110 frozen source links/13 ZIP members/9 roles/pending-only policy; not a firmware test')
if __name__=='__main__':main()
