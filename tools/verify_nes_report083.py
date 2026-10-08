# SPDX-License-Identifier: MIT
"""Check frozen083 host/ARM/trial/restore inputs without rerunning tests."""
from pathlib import Path
import argparse,json,zipfile
from nes_report083_prepare import ROOT,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 m=json.loads((ROOT/'analysis/report-observation083-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for mode in ['normal','no-readback-compare','no-reset-rehold','no-early-marker','no-marker-rehold']:
  d=e/'work'/(mode+'-03');r=json.loads((d/'result.json').read_bytes())
  assert r['mode']==mode and r['exit']==(0 if mode=='normal' else 3) and not r['physical']
  for n,h in r['files'].items():assert sha(d/n)==h,(mode,n)
  for n,h in r['inputs'].items():
   if n.startswith('public/'):assert sha(ROOT/n[7:])==h,n
  assert sha(d/'executed-driver.py')==sha(ROOT/'tools/test_nes_report_observation083.py')
 d=e/'work/normal-03';assert 'PASS083 checks=679' in (d/'run.log').read_text()
 assert 'PASS083 TIMER checks=5' in (d/'timer.log').read_text()
 arm=e/'work/arm-01';c=json.loads((arm/'arm-check083.json').read_bytes());s=arm/'source/src'
 assert c['order']==['report_boot080','marker083','sdn_report_initialize081','marker083','file_init','sdinv_write_report']
 assert sha(s/'obj-report079/firmware.stm')==c['firmware_sha256']==m['firmware_sha256']
 assert sha(s/'nes_report_platform083.c')==sha(d/'nes_report_platform083.c')==sha(ROOT/'src/nes/firmware/nes_report_platform083.c')
 prep=json.loads((arm/'preparation083.json').read_bytes())
 for n in c['unchanged_inputs']:assert sha(s/n)==prep['inputs']['work/arm-02/source/src/'+n],n
 package=e/'package-02';pc=json.loads((package/'package-check083.json').read_bytes())
 assert pc['full_member_readback'] and not pc['hardware_verified'] and not pc['installed']
 for k,suffix in [('trial','TRIAL'),('source','SOURCE')]:
  zpath=package/('FXPAK-SDREPORT083-'+suffix+'.zip');assert sha(zpath)==pc[k]['sha256']
  import hashlib
  with zipfile.ZipFile(zpath) as z:
   assert z.testzip() is None and set(z.namelist())==set(pc[k]['members'])
   for n,h in pc[k]['members'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 assert pc['restore_sha256']=='1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b'
 assert m['report_only_trial_ready'] and not m['hardware_verified'] and not m['nes_cf68_installable']
 print('PASS083 host679/timer5/causal4/ARM order/trial+source ZIP readback/exact044 restore; physical=0')
if __name__=='__main__':main()
