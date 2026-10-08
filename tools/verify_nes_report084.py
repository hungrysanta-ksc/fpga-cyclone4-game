# SPDX-License-Identifier: MIT
"""Verify frozen084 evidence; private pinned inputs are required."""
from pathlib import Path
import argparse,json,hashlib,zipfile
from nes_report084_prepare import ROOT,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 m=json.loads((ROOT/'analysis/report-space084-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for mode in ['normal','no-readback-compare','no-reset-rehold','no-early-marker','no-marker-rehold','no-space-scan']:
  d=e/'work'/(mode+'-05');r=json.loads((d/'result.json').read_bytes())
  assert r['mode']==mode and r['exit']==(0 if mode=='normal' else 3) and not r['physical']
  for n,h in r['files'].items():assert sha(d/n)==h,(mode,n)
  for n,h in r['inputs'].items():
   if n.startswith('public/'):assert sha(ROOT/n[7:])==h,n
  assert sha(d/'executed-driver.py')==sha(ROOT/'tools/test_nes_report_space084.py')
 d=e/'work/normal-05';assert 'PASS084 checks=809' in (d/'run.log').read_text()
 assert 'PASS083 TIMER checks=5' in (d/'timer.log').read_text()
 assert 'stage=3 fault=16 commands=44 writes=1 bytes=0 ticks=300' in (e/'occupied-repro/occupied-run.log').read_text()
 repro=json.loads((e/'occupied-repro/provenance084.json').read_bytes())
 for n,h in repro['unchanged083_sources'].items():assert sha(e/'occupied-repro'/n)==h,n
 arm=e/'work/arm-01';s=arm/'source/src';c=json.loads((arm/'arm-check084.json').read_bytes())
 assert c['order']==['report_boot080','marker084','sdn_report_initialize081','marker084','file_init','marker084','report_space084','sdinv_write_report']
 assert sha(s/'obj-report079/firmware.stm')==c['firmware_sha256']==m['firmware_sha256']
 for n in ['nes_report_platform084.c','nes_report_space084.c','nes_report_layout084.h','nes_report_boot080.c','nes_report_checkpoint079.c']:
  assert sha(s/n)==sha(d/n),n
 prep=json.loads((arm/'preparation084.json').read_bytes())
 for n in c['unchanged_inputs']:assert sha(s/n)==prep['inputs']['work/arm-02/source/src/'+n],n
 package=e/'package-01';pc=json.loads((package/'package-check084.json').read_bytes())
 for k,suffix in [('trial','TRIAL'),('source','SOURCE')]:
  zpath=package/('FXPAK-SDREPORT084-'+suffix+'.zip');assert sha(zpath)==pc[k]['sha256']
  with zipfile.ZipFile(zpath) as z:
   assert z.testzip() is None and set(z.namelist())==set(pc[k]['members'])
   for n,h in pc[k]['members'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 assert pc['restore_sha256']=='1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b'
 assert m['report_only_trial_ready'] and not m['hardware_verified'] and not m['nes_cf68_installable']
 print('PASS084 repro083/host809/timer5/causal5/ARM order/ZIP readback/exact044 restore; physical fix unverified')
if __name__=='__main__':main()
