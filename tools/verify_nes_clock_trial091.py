# SPDX-License-Identifier: MIT
"""Audit091 frozen transition proof and every delivered ZIP member, read only."""
from pathlib import Path
import argparse,json,hashlib,zipfile
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence.resolve()
 m=json.loads((ROOT/'analysis/clock-trial091-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():
  q=(e/n).resolve();assert q.is_relative_to(e) and sha(q)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 read=lambda n:json.loads((e/n).read_bytes())
 normal=read('pins04/result.json');assert normal['checks']==94 and normal['configuration_rising_edges_per_success']==6543555
 for n in ['no-af-restore','no-spi-restore','no-data-input']:
  r=read(n+'02/result.json');log=(e/(n+'02')/'host.log').read_text(errors='replace');assert r['mutation']==n and 'Assertion failed' in log and r['expected_failure'] in log
 package=read('package-01/package-check091.json')
 for role,label in [('trial','TRIAL'),('source','SOURCE')]:
  q=e/'package-01'/('FXPAK-CLOCKREPORT090-'+label+'.zip');assert sha(q)==package[role]['sha256']
  with zipfile.ZipFile(q) as z:
   assert set(z.namelist())==set(package[role]['members']) and z.testzip() is None
   for n,h in package[role]['members'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 prior=json.loads((ROOT/'analysis/clock-report090-verification.json').read_bytes())
 for n,h in prior['public_sources'].items():assert sha(ROOT/n)==h,n
 assert m['firmware_sha256']==prior['firmware_sha256']==package['firmware_sha256']
 assert m['report_trial_ready'] and not m['nes_installable'] and not m['hardware_execution']
 target=json.loads((ROOT/'cores/nes/first-game-target.json').read_bytes());assert target['mapper']==4 and target['prg_rom_bytes']==262144 and target['chr_rom_bytes']==131072 and target['file_bytes']==393232
 print('PASS091: actual GPIO helper/macro register model94+3 controls, exact090/044 trial+source ZIP readback, SMB3 first target recorded; physical return pending.')
if __name__=='__main__':main()
