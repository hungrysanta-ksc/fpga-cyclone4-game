# SPDX-License-Identifier: MIT
"""Frozen128 implementation/tests and actual fit; never equates fit with IO signoff."""
from pathlib import Path
import argparse,csv,json,re
from nes_command128 import ROOT,sha
from review_nes_command128 import inspect
def review(e):
 t=e/'test06';b=e/'boot05';f=e/'fit07';d=e/'diff02'
 m=json.loads((t/'result128.json').read_bytes());bm=json.loads((b/'boot128.json').read_bytes())
 assert m['passed'] and bm['passed'] and bm['cancellations']==24 and bm['misuse_ready_fixtures']==6 and bm['missing_latch_rejected']
 for case in m['cases']:
  log=(t/(case['name']+'.log')).read_text(errors='replace');assert case['expected'] in log
  if case['expected'].startswith('PASS'):assert '** Fatal:' not in log and 'PASS128 boundary' in log
  else:assert '** Fatal:' in log
 for directory,meta in [(t,m),(b,bm)]:
  for n,h in meta['sources'].items():assert sha(directory/n)==h,n
 dm=json.loads((d/'diff128.json').read_bytes())
 assert dm['passed'] and dm['one_step_cases']==26112 and dm['negative_error_code_rejected']
 for n,h in dm['sources'].items():assert sha(d/n)==h,n
 assert 'PASS128 DIFF one_step_cases=26112' in (d/'diff.log').read_text()
 assert '** Fatal: DIFF128' in (d/'negative.log').read_text()
 assert 'PASS128 OWN misuse_ready_fixtures=6' in (b/'boot.log').read_text()
 assert '** Fatal: LOADER127 OWN128 direct post-fault DATA blocked' in (b/'negative-latch.log').read_text()
 assert sha(t/'nes_rom_spi.sv')==sha(f/'nes_rom_spi.sv')==sha(ROOT/'src/nes/diagnostic/nes_rom_spi128.sv')
 assert sha(d/'nes_rom_loader.sv')==sha(f/'nes_rom_loader.sv')==sha(ROOT/'src/nes/diagnostic/nes_rom_loader128.sv')
 for n in ['nes_rom_loader.sv','nes_rom_physical.sv','nes_rom_boot.sv','nes_spi_boot.sv','nes_domain_reset124.sv','nes_diag_clock_guard127.sv']:
  assert sha(b/n)==sha(f/n),n
 q=(f/'live.qsf').read_text();assert 'FITTER_EFFORT' not in q
 for line in (ROOT/'src/nes/diagnostic/nes_bridge_sync126.qsf').read_text().splitlines():
  if line.startswith('set_instance_assignment'):assert line in q
 assert not re.search(r'^\s*set_(false_path|clock_groups|multicycle_path)',(f/'live.sdc').read_text(),re.M)
 meta=json.loads((f/'review128.json').read_bytes());base=inspect(f)
 assert {k:meta[k] for k in base}==base
 topology=list(csv.DictReader((f/'topology126.tsv').open(),delimiter='\t'))
 first=[x for x in topology if x['stage']=='0'];assert len(first)==1 and first[0]['to'].endswith('release_reset[1]')
 times=list(csv.DictReader((f/'timing126.tsv').open(),delimiter='\t'));assert len(times)==6 and min(float(x['slack']) for x in times)>=0
 local=list(csv.DictReader((f/'local-reset126.tsv').open(),delimiter='\t'))
 assert len(local)==meta['diagnostic_reset_chain']['local_release_paths']
 assert min(float(x['slack']) for x in local)==meta['diagnostic_reset_chain']['min_local_release_slack_ns']
 decoder=re.search(r'PASS SPI CHECK CONTROL checks=(\d+) negative_cases=(\d+)',(t/'decoder.log').read_text());assert decoder
 boot=re.search(r'PASS127 LOADER pin_writes=(\d+) check_reads=(\d+) run_reads=(\d+) drains=(\d+)',(b/'boot.log').read_text());assert boot
 for label in ['decoder','decoder-fast']:
  log=(t/(label+'.log')).read_text();assert 'PASS128 boundary' in log
  assert re.search(r'checks='+decoder[1]+r' negative_cases='+decoder[2],log)
 assert (b/'boot.log').read_text().count('PASS128 BOOT cancellations=24')==2
 return dict(final_fit=meta,decoder_checks_per_speed=int(decoder[1]),decoder_negatives_per_speed=int(decoder[2]),half_sck_ns=[60,18],additional_ordered_acks_per_speed=512,retirement_boundaries=['hard-fault-before-START','raw-reset-queued-START','stopped-clock-reset-hold','overlapping-frame'],boot_counts=list(map(int,boot.groups())),check_cancel_positions_per_image=24,check_cancel_total=48,seeded_ready_misuse_cases=6,loader_one_step_cases=26112,causal_rejections=['unverified-START','fault-priority-removed','sticky-DATA-gate-removed','loader-error-code-changed'],full_spi_cpu_session=False,installable=False)
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 m=json.loads((ROOT/'analysis/command128-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 assert review(e)==m['checks'];print('PASS128 frozen implementation/test/fit evidence; full timing and installation remain separate')
if __name__=='__main__':main()
