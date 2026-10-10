# SPDX-License-Identifier: MIT
"""Verify the immutable136 record and exact released trial pair."""
from pathlib import Path
import argparse,json,zipfile,hashlib
from nes_spi_boot import ROOT,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 m=json.loads((ROOT/'analysis/run136-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 package=m['package'];zpath=e/'release01/NES136-MINIMUM-RUN-and-RESTORE044.zip'
 assert sha(zpath)==package['zip_sha256'] and package['normal_trial_ready'] and not package['physical']
 with zipfile.ZipFile(zpath) as z:
  manifest=json.loads(z.read('manifest.json'));assert len(z.namelist())==12
  for n,d in manifest['files'].items():
   b=z.read(n);assert len(b)==d['bytes'] and hashlib.sha256(b).hexdigest()==d['sha256'],n
  assert z.read('01-RUN136-SD-ROOT/NES RUN 136.nh1')==b''
  fw=z.read('01-RUN136-SD-ROOT/sd2snes/firmware.stm');assert hashlib.sha256(fw).hexdigest()==package['firmware_sha256']
  assert b'NES-RUN136' in fw and b'nes-run-last-136.txt' in fw
  assert b'NES VERIFY 094 80.nh1' not in fw
 c=(e/'arm03/src/nes_run136.inc').read_text();assert 's.flags!=2||s.count!=total' in c
 assert 'for(unsigned i=0;i<16;i++)' in c
 assert len(json.loads((e/'host05/result.json').read_bytes())['cases'])==8
 rtl=json.loads((e/'rtl02/result.json').read_bytes());assert rtl['passed'] and len(rtl['results'])==2
 assert all('first=3430 last=73722 stopped=75636' in s for s in rtl['results'])
 arm=json.loads((e/'arm-check03/result.json').read_bytes());assert arm['strong_nmi'] and arm['host_sources_match'] and arm['firmware_sha256']==package['firmware_sha256']
 print('PASS136 immutable evidence,8 MCU cases,2 RTL phases,ARM and12-member trial/restore pair')
if __name__=='__main__':main()
