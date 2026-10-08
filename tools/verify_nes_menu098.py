# SPDX-License-Identifier: MIT
"""Verify frozen098 actual caller/loader evidence; requires private inputs."""
from pathlib import Path
import argparse,json
from nes_spi_boot import ROOT,sha
from test_nes_menu098 import definition
from nes_menu098 import once

NORMAL=['suite03','fat32-96-02','fat32-96-fault02']
NEGATIVE=['negative-entry02','negative-copy02','negative-prepared02','negative-postrelease02']
PUBLIC=['tools/nes_menu098.py','tools/test_nes_menu098.py','tools/prepare_nes_menu098_arm.py','tools/build_nes_menu098_arm.ps1','tools/check_nes_menu098_arm.py','tools/verify_nes_menu098.py','tests/nes-functional/menu098_host.c']

def verify_runs(root,prefix=''):
 total=0
 for name in NORMAL+NEGATIVE+['baseline04']:
  d=root/(prefix+name);r=json.loads((d/'result.json').read_bytes())
  for n,h in r['files'].items():assert sha(d/n)==h,(name,n)
  assert sha(d/'executed-driver.py')==sha(ROOT/'tools/test_nes_menu098.py')
  assert sha(d/'executed-adapter.py')==sha(ROOT/'tools/nes_menu098.py')
  assert sha(d/'host098.c')==sha(ROOT/'tests/nes-functional/menu098_host.c')
  assert (d/'load098.inc').read_text()==definition((d/'memory.c').read_text(),'load_rom')
  assert (d/'reliable098.inc').read_text()==definition((d/'original-memory.c').read_text(),'sram_reliable')
  raw=(d/'original-main.c').read_text()
  pending=raw[raw.index('    if(nes_menu_diagnostic_pending()) {'):raw.index('    while(get_cic_state() == CIC_FAIL)')]
  ready=raw[raw.index('nes_return_menu_ready:'):raw.index('    while(!cmd) {')]
  body='static bool actual_main098(void){\n'+pending+'assert(!"pending path required");\n'+ready+'return true;\n}\n'
  if name not in NEGATIVE:assert (d/'main098.inc').read_text()==body
  for case in r['cases']:
   log=d/('case-'+str(case['scenario'])+'.log');assert sha(log)==case['log_sha256']
   assert case['last']==log.read_text().strip().splitlines()[-1]
  if name in NEGATIVE:
   assert len(r['cases'])==1 and r['cases'][0]['exit']!=0 and 'Assertion failed:' in r['cases'][0]['last']
  else:
   assert not r['mutation'] and all(c['exit']==0 and c['last'].startswith('PASS098') for c in r['cases'])
   if name=='baseline04':assert r['baseline'] and 'REPRO098 actual main 0xC00000 rejected' in (d/'case-0.log').read_text()
   else:
    assert not r['baseline'];total+=len(r['cases'])
    expected=once((d/'original-memory.c').read_text(),'||flags||base_addr)','||flags||base_addr!=SRAM_MENU_ADDR)')
    assert (d/'memory.c').read_text()==expected
 assert total==26
 r=json.loads((root/(prefix+'suite03')/'result.json').read_bytes());assert {c['scenario'] for c in r['cases']}==set(range(15))|set(range(20,29))
 arm=root/(prefix+'arm01');check=json.loads((arm/'check098.json').read_bytes())
 fw=arm/'src/obj-nes-098/firmware.stm';elf=arm/'src/obj-nes-098/sd2snes.elf'
 assert sha(fw)==check['firmware_sha256'] and fw.stat().st_size==check['firmware_bytes']==180952
 assert sha(elf)==check['elf_sha256']
 for n,h in check['host_arm_identical'].items():assert sha(arm/'src'/n)==h==sha(root/(prefix+'suite03')/n)
 for n,h in check['retained094'].items():assert sha(arm/'src'/n)==h
 assert not check['physical'] and not check['installable']
 # Publication removed an extra blank EOF line; executed bytes stay frozen.
 assert (arm/'executed-builder.ps1').read_bytes().rstrip(b'\r\n')==(ROOT/'tools/build_nes_menu098_arm.ps1').read_bytes().rstrip(b'\r\n')

def main():
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--runs-root',type=Path);g.add_argument('--evidence',type=Path);a=p.parse_args()
 if a.runs_root:verify_runs(a.runs_root,'nes-menu098-')
 else:
  e=a.evidence.resolve();m=json.loads((ROOT/'analysis/menu098-verification.json').read_bytes())
  assert sha(e/'manifest.json')==m['manifest_sha256']
  pins=json.loads((e/'manifest.json').read_bytes())['files'];assert len(pins)==m['archived_files']
  for n,h in pins.items():assert (e/n).resolve().is_relative_to(e) and sha(e/n)==h,n
  for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
  assert m['host_cases']==26 and m['causal_controls']==4 and not m['installable']
  verify_runs(e)
 print('PASS098: original caller rejection;26 cases/4 controls;full load_rom/main spans;matched ARM;lower IO/physical open')
if __name__=='__main__':main()
