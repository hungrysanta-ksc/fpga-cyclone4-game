# SPDX-License-Identifier: MIT
"""Verify131 active-counter equivalence, full writes and fitted timing."""
from pathlib import Path
import argparse,csv,json,tempfile,re
from nes_counter131 import ROOT,sha,materialize
from review_nes_counter131 import inspect

def rows(p):return list(csv.DictReader(p.open(),delimiter='\t'))

def review(e):
 d=e/'diff01';t=e/'test02';f=e/'fit05'
 dm=json.loads((d/'diff131.json').read_bytes());tm=json.loads((t/'test131.json').read_bytes())
 assert dm['passed'] and dm['one_step_cases']==26112 and dm['negative_preload_rejected']
 assert tm['passed'] and tm['full_writes_repeated'] and tm['full_image_bytes']==[81920,98304]
 for directory,meta in [(d,dm),(t,tm)]:
  for n,h in meta['sources'].items():assert sha(directory/n)==h,n
 assert 'PASS131 DIFF one_step_cases=26112' in (d/'diff.log').read_text()
 assert '** Fatal:' not in (d/'diff.log').read_text()
 assert '** Fatal: DIFF131 active counter' in (d/'negative.log').read_text()
 log=(t/'normal.log').read_text();assert '** Fatal:' not in log
 for value in ['pin_writes=180311 check_reads=308 run_reads=128 drains=86','PASS129 reader cancellations=96 stopped_clock_cases=3','PASS128 OWN misuse_ready_fixtures=6']:
  assert value in log,value
 assert log.count('PASS128 BOOT cancellations=24')==2
 for n in ['nes_rom_loader.sv','nes_rom_boot.sv','nes_rom_physical.sv']:
  def behavior(p):return re.sub(rb'\(\* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF[^"]*" \*\) ',b'',p.read_bytes())
  assert behavior(d/n)==behavior(t/n)==behavior(f/n),n
 for n in ['nes_counter131.py','nes_counter131_fit.py']:
  assert sha(f/('executed-'+n))==sha(ROOT/'tools'/n)
 assert sha(t/'executed-nes_counter131_test.py')==sha(ROOT/'tools/nes_counter131_test.py')
 assert sha(d/'executed-diff.py')==sha(ROOT/'tools/nes_counter131_diff.py')
 assert sha(d/'counter131_diff_tb.sv')==sha(ROOT/'tests/nes-functional/counter131_diff_tb.sv')
 prior=e.parents[1]/'nes-enable130/evidence'
 pm=json.loads((ROOT/'analysis/enable130-verification.json').read_bytes())
 assert sha(prior/'manifest.json')==pm['manifest_sha256']
 pins=json.loads((prior/'manifest.json').read_bytes())['files']
 inputs=json.loads((f/'materialization131.json').read_bytes())
 for n,h in inputs['inputs'].items():
  assert h==pins['fit01/'+n]==sha(prior/'fit01'/n)
  assert sha(f/n)==inputs['outputs'][n]
  if n=='nes_rom_spi.sv':
   assert (f/n).read_text().count('AUTO_CLOCK_ENABLE_RECOGNITION OFF')==2
   assert behavior(f/n)==(prior/'fit01'/n).read_bytes()
  elif n!='nes_rom_loader.sv':assert sha(f/n)==h,n
 assert (d/'reference127.sv').read_text()==(prior/'fit01/nes_rom_loader.sv').read_text().replace('module nes_rom_loader #','module nes_rom_loader_reference #')
 with tempfile.TemporaryDirectory(prefix='nes-counter131-identity-') as name:
  out=Path(name);materialize(out,e.parents[1],full=True)
  assert json.loads((out/'materialization131.json').read_bytes())==inputs
 assert json.loads((f/'fit131.json').read_bytes())['phases']==[dict(phase=x,returncode=0) for x in ['map','fit','sta']]
 meta=json.loads((f/'review131.json').read_bytes());core=inspect(f)
 assert {k:meta[k] for k in core}==core
 ports=rows(f/'state131-edges.tsv');assert len({x['register'] for x in ports})==16
 assert not [x for x in ports if '|state.' in x['register'] and x['source'].endswith('|ena')]
 paths=rows(f/'state131-timing.tsv')
 for kind in ['setup','hold']:
  assert meta['loader_ports']['minimum_'+kind+'_ns']==min(float(x['slack']) for x in paths if x['type']==kind)
 deps=rows(f/'counter131-dependencies.tsv')
 assert len(deps)==6 and all(x['paths']=='0' for x in deps if x['group']=='loaded_count')
 assert min(float(x['slack']) for x in deps if x['group']=='check_failed')==meta['counter_dependencies']['check_failed_minimum_setup_ns']
 index=rows(f/'index131-edges.tsv');assert len({x['register'] for x in index})==17 and not [x for x in index if x['source'].endswith('|ena')]
 assert '** Fatal: LOADER127 OWNER129 no additional writes from reader tests' in (e/'test01/normal.log').read_text()
 old={n:inspect(e/n) for n in ['fit01','fit02','fit03','fit04']}
 for n in old:assert behavior(e/n/'nes_rom_loader.sv')==behavior(f/'nes_rom_loader.sv')
 address=rows(f/'address131-edges.tsv');assert 0<len({x['register'] for x in address})<=22
 assert not [x for x in address if x['source'].endswith(('|ena','|sload','|sclr'))]
 checked=rows(f/'checked131-edges.tsv');assert len({x['register'] for x in checked})==8
 assert len([x for x in checked if x['source'].endswith('|ena')])==8
 assert not [x for x in checked if x['source'].endswith(('|sload','|sclr'))]
 assert meta['same_clock_setup_pass'] and meta['same_clock_hold_pass']
 assert sha(f/'state131.tcl')==sha(ROOT/'tools/nes_counter131_paths.tcl')
 return dict(selected='test02/fit05',final_fit=meta,unadopted_fits=old,one_step_cases=26112,preload_mutation_rejected=True,inactive_counter_not_compared=True,full_image_writes_bytes=[81920,98304],pin_writes_including_faults=180311,write_fault_positions=86,check_reads=308,run_reads=128,check_cancel_cases=48,additional_cancel_cases=96,stopped_clocks=3,ready_misuse_cases=6,full_spi_cpu_mcu_session=False,installable=False)

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence
 m=json.loads((ROOT/'analysis/counter131-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 entries=json.loads((e/'manifest.json').read_bytes())['files'];assert len(entries)==m['archived_files']
 for n,h in entries.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 assert review(e)==m['checks'];print('PASS131 frozen sources, full-write regression and fitted timing; installation remains separate')
if __name__=='__main__':main()
