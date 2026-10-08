# SPDX-License-Identifier: MIT
"""Read-only verification of the RTC099 evidence and public source pins."""
from pathlib import Path
import argparse,json
from nes_spi_boot import ROOT,sha

PUBLIC=['tools/nes_rtc099.py','tools/prepare_nes_rtc099_arm.py','tools/build_nes_rtc099_arm.ps1','tools/test_nes_rtc099.py','tools/check_nes_rtc099_arm.py','tools/verify_nes_rtc099.py','tests/nes-functional/rtc099_model.h','tests/nes-functional/rtc099_unit.c']
NORMAL=['unit05','main04','fat32-96-01']
NEGATIVE=['negative-'+n+'01' for n in ['poll','time','cleanup','fault','baseline']]

def verify_runs(e):
 arm=json.loads((e/'arm01/check099.json').read_bytes());total=0
 for name in NORMAL+NEGATIVE:
  d=e/name;r=json.loads((d/'result.json').read_bytes())
  for i,c in enumerate(r['cases']):
   log=d/f'case-{i}.log';assert sha(log)==c['log_sha256']
   assert log.read_text().strip().splitlines()[-1]==c['last']
   if name in NORMAL:assert c['exit']==0 and c['last'].startswith('PASS099');total+=1
   else:assert c['exit']!=0 and 'Assertion' in log.read_text()
  if name in NORMAL:
   assert sha(d/'rtc099-production.c')==r['rtc_sha256']==arm['rtc_sha256']
   assert sha(d/'nes_diag_runtime.h')==arm['runtime_header_sha256']
 assert total==30
 fw=e/'arm01/src/obj-nes-099/firmware.stm';elf=e/'arm01/src/obj-nes-099/sd2snes.elf'
 assert fw.stat().st_size==arm['firmware_bytes']==181200 and sha(fw)==arm['firmware_sha256']
 assert sha(elf)==arm['elf_sha256']
 assert sha(e/'arm01/src/stm32f4xx/rtc.c')==arm['rtc_sha256']
 assert (e/'main04/main098.inc').read_bytes()==(e/'fat32-96-01/main098.inc').read_bytes()
 assert (e/'arm01/executed-builder.ps1').read_bytes()==(ROOT/'tools/build_nes_rtc099_arm.ps1').read_bytes()

def main():
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--runs',type=Path);g.add_argument('--evidence',type=Path);a=p.parse_args()
 e=(a.runs or a.evidence).resolve()
 if a.evidence:
  m=json.loads((ROOT/'analysis/rtc099-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
  pins=json.loads((e/'manifest.json').read_bytes())['files'];assert len(pins)==m['archived_files']
  for n,h in pins.items():assert (e/n).resolve().is_relative_to(e) and sha(e/n)==h,n
  for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
  assert not m['physical'] and not m['installable']
 verify_runs(e);print('PASS099:30 cases/4 causal controls/original unbounded wait/linked ARM; physical and lower IO open')
if __name__=='__main__':main()
