# SPDX-License-Identifier: MIT
"""Read-only verification of frozen lower100 code, runs and ARM evidence."""
from pathlib import Path
import argparse,json
from nes_spi_boot import ROOT,sha
from test_nes_lower100 import MEM,FPGA,SPI
from test_nes_menu098 import definition
PUBLIC=['tools/nes_lower100.py','tools/prepare_nes_lower100.py','tools/build_nes_lower100_arm.ps1','tools/test_nes_lower100.py','tools/check_nes_lower100_arm.py','tools/verify_nes_lower100.py','tests/nes-functional/lower100_model.h','tests/nes-functional/lower100_unit.inc']
NORMAL=['unit03','main01','fat32-96-01']
NEGATIVE=['negative-'+n+'01' for n in ['select','async','budget','drain','ready','baseline']]

def verify_runs(e):
 arm=json.loads((e/'arm02/check100.json').read_bytes());total=0
 for name in NORMAL+NEGATIVE:
  d=e/name;r=json.loads((d/'result.json').read_bytes())
  assert sha(d/'executed-driver.py')==sha(ROOT/'tools/test_nes_lower100.py')
  for i,c in enumerate(r['cases']):
   log=d/f'case-{i}.log';assert sha(log)==c['log_sha256']
   assert log.read_text().strip().splitlines()[-1]==c['last']
   if name in NORMAL:assert c['exit']==0 and c['last'].startswith('PASS100');total+=1
   else:assert c['exit']!=0 and 'Assertion' in log.read_text()
  for n,h in r['production'].items():assert sha(d/('production-'+n.replace('/','-')))==h
  if name in NORMAL:
   for n in r['production']:assert (d/('production-'+n.replace('/','-'))).read_text()==(e/'arm02/src'/n).read_text()
   assert (d/'spi100-original.inc').read_text()=='\n'.join(definition((e/'arm02/src/stm32f4xx/spi.c').read_text(),n) for n in SPI)
 assert total==34
 s=e/'arm02/src';fw=s/'obj-nes-100/firmware.stm';elf=s/'obj-nes-100/sd2snes.elf'
 assert fw.stat().st_size==arm['firmware_bytes']==182404 and sha(fw)==arm['firmware_sha256']
 assert sha(elf)==arm['elf_sha256']
 for n,h in arm['retained099'].items():assert sha(s/n)==h
 for n,h in arm['host_arm_normalized_identical'].items():assert sha(s/n)==h
 assert (e/'main01/main098.inc').read_bytes()==(e/'fat32-96-01/main098.inc').read_bytes()
 assert (e/'arm02/executed-builder.ps1').read_bytes()==(ROOT/'tools/build_nes_lower100_arm.ps1').read_bytes()

def main():
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--runs',type=Path);g.add_argument('--evidence',type=Path);a=p.parse_args();e=(a.runs or a.evidence).resolve()
 if a.evidence:
  m=json.loads((ROOT/'analysis/lower100-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
  pins=json.loads((e/'manifest.json').read_bytes())['files'];assert len(pins)==m['archived_files']
  for n,h in pins.items():assert (e/n).resolve().is_relative_to(e) and sha(e/n)==h,n
  for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
  assert not m['physical'] and not m['installable']
 verify_runs(e);print('PASS100:34 cases/5 causal controls/original CS counterexample/linked ARM; peripheral timing remains open')
if __name__=='__main__':main()
