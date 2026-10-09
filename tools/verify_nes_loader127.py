# SPDX-License-Identifier: MIT
"""Verify frozen127 evidence; fitting success is deliberately not timing approval."""
from pathlib import Path
import argparse,json,re
from nes_loader127 import ROOT,sha
from review_nes_loader127 import inspect
def review(e):
 u=e/'unit02';d=e/'decoder02';f=e/'fit02'
 um=json.loads((u/'result127.json').read_bytes());dm=json.loads((d/'result127.json').read_bytes())
 assert um['passed'] and dm['passed'] and len(um['cases'])==6 and len(dm['cases'])==3
 for directory,meta in [(u,um),(d,dm)]:
  for case in meta['cases']:
   log=(directory/(case['name']+'.log')).read_text(errors='replace');assert case['expected'] in log
   if case['expected'].startswith('PASS'):assert '** Fatal:' not in log
  for n,h in meta['sources'].items():assert sha(directory/n)==h,n
 for n in ['nes_rom_loader.sv','nes_rom_boot.sv','nes_rom_physical.sv','nes_spi_boot.sv','nes_diag_clock_guard127.sv','nes_diag_startup_guard.sv','nes_domain_reset124.sv']:
  assert sha(u/n)==sha(d/n)==sha(f/n),n
 assert sha(d/'nes_rom_spi.sv')==sha(f/'nes_rom_spi.sv')
 for n in ['nes_rom_loader127.sv','nes_diag_clock_guard127.sv']:
  dst='nes_rom_loader.sv' if n.startswith('nes_rom_loader') else n
  assert sha(ROOT/'src/nes/diagnostic'/n)==sha(f/dst)
 for n in ['nes_loader127.py','nes_loader127_fit.py']:
  assert sha(ROOT/'tools'/n)==sha(f/('executed-'+n))
 # Publication removed one space-only blank line; executed bytes remain frozen.
 executed=(d/'executed-nes_loader127_decoder.py').read_text()
 assert executed.count('\n \n')==1
 assert (ROOT/'tools/nes_loader127_decoder.py').read_text()==executed.replace('\n \n','\n\n')
 qsf=(f/'live.qsf').read_text()
 for line in (ROOT/'src/nes/diagnostic/nes_bridge_sync126.qsf').read_text().splitlines():
  if line.startswith('set_instance_assignment'):assert line in qsf
 assert not re.search(r'^\s*set_(false_path|clock_groups|multicycle_path)',(f/'live.sdc').read_text(),re.M)
 top=(f/'nes_live_joint.sv').read_text();assert 'assign run_enable=ext_arm' not in top and 'nes_spi_boot loader_boot' in top
 assert 'WAIT_CYCLES(33603)' in top and 'READ_CYCLES(16)' in (f/'nes_rom_boot.sv').read_text()
 final=inspect(f);assert final==json.loads((f/'review127.json').read_bytes())
 assert final['fit_passed'] and not final['same_clock_setup_pass'] and not final['installable']
 old=inspect(e/'fit01');assert old['raw_clock_pair_min_ns']==-9.959
 match=re.search(r'PASS127 LOADER pin_writes=(\d+) check_reads=(\d+) run_reads=(\d+) drains=(\d+)',(u/'loader.log').read_text());assert match
 counts=list(map(int,match.groups()));assert counts==[180311,260,128,86]
 return dict(final_fit=final,loader_counts=dict(zip(['pin_writes','check_reads','run_reads','write_hold_fault_positions'],counts)),decoder_checks_per_speed=149,decoder_negative_cases_per_speed=18,decoder_half_sck_ns=[60,18],guard_cases=3,causal_rejections=['write63cycles','unverified_RUN','old31cycle_timeout'],unchanged_loader_guard_reused=True,full_spi_cpu_session=False,installable=False)
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 meta=json.loads((ROOT/'analysis/loader127-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==meta['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
 assert review(e)==meta['checks'];print('PASS127 integrity/function/fit evidence;168MHz timing remains FAILED, installable=false')
if __name__=='__main__':main()
