# SPDX-License-Identifier: MIT
"""Verify frozen080 private evidence and exact public sources without reruns."""
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 meta=json.loads((ROOT/'analysis/report-platform080-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256'];files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==meta['files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
 for mode in ['normal','no-compare','no-final-guard']:
  d=e/'work'/(mode+'-03');r=json.loads((d/'result.json').read_bytes());assert r['mode']==mode and not r['physical'] and r['exit']==(0 if mode=='normal' else 3)
  for n,h in r['files'].items():assert sha(d/n)==h,(mode,n)
  assert sha(d/'executed-driver.py')==sha(ROOT/'tools/test_nes_report_boot080.py')
  assert sha(d/'host.c')==sha(ROOT/'tests/nes-functional/report_boot080_host.c')
  if mode=='normal':assert 'PASS080 checks=881' in (d/'run.log').read_text()
 arm=e/'work/arm-02';src=arm/'source/src';c=json.loads((arm/'arm-check080.json').read_bytes());prep=json.loads((arm/'preparation080.json').read_bytes())
 assert not c['installable'] and not c['arm_executed']
 assert sha(src/'obj-report079/firmware.stm')==c['firmware_sha256']==meta['firmware_sha256']
 assert sha(src/'obj-report079/sd2snes.elf')==c['elf_sha256']
 for n in c['unchanged_native']:assert sha(src/n)==prep['inputs']['work/arm-03/source/src/'+n],n
 for n in ['nes_report_boot080.h','nes_report_boot080.c','nes_report_decode080.c','nes_report_platform080.c']:assert sha(src/n)==sha(ROOT/'src/nes/firmware'/n),n
 assert c['edges']['write_report -> sdinv_checkpoint079']==7
 print('PASS080 frozen881/causal2/ARM, exact public/executed inputs; init/native full session and physical pending')
if __name__=='__main__':main()
