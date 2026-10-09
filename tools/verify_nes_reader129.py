# SPDX-License-Identifier: MIT
"""Verify frozen129 scope, source identity and actual timing, not install approval."""
from pathlib import Path
import argparse,csv,json,re
from nes_reader129 import ROOT,sha
from review_nes_reader129 import inspect

def review(e):
 t=e/'test01';f=e/'fit01'
 m=json.loads((t/'test129.json').read_bytes())
 assert m['passed'] and not m['full_writes_repeated']
 for n,h in m['sources'].items():assert sha(t/n)==h,n
 for n in ['nes_rom_loader.sv','nes_rom_boot.sv','nes_rom_physical.sv']:
  assert sha(t/n)==sha(f/n),n
 assert sha(f/'nes_rom_loader.sv')==sha(ROOT/'src/nes/diagnostic/nes_rom_loader128.sv')
 assert sha(f/'nes_rom_spi.sv')==sha(ROOT/'src/nes/diagnostic/nes_rom_spi128.sv')
 assert sha(f/'executed-nes_reader129.py')==sha(ROOT/'tools/nes_reader129.py')
 assert sha(t/'executed-nes_reader129_test.py')==sha(ROOT/'tools/nes_reader129_test.py')
 normal=(t/'normal.log').read_text();assert '** Fatal:' not in normal
 assert normal.count('PASS128 BOOT cancellations=24')==2
 for text in ['PASS128 OWN misuse_ready_fixtures=6','PASS129 reader cancellations=96 stopped_clock_cases=3','pin_writes=87 check_reads=308 run_reads=128 drains=86']:assert text in normal,text
 assert '** Fatal: LOADER127 OWNER129 captured mode' in (t/'negative-owner.log').read_text()
 assert '** Fatal: LOADER127 CANCEL129 owner cleared' in (t/'negative-async.log').read_text()
 experiments=[]
 for tn,dn,fn in [('test02','diff01','fit03'),('test03','diff02','fit04')]:
  dt=e/dn;tt=e/tn;ff=e/fn
  dm=json.loads((dt/'diff129.json').read_bytes());tm=json.loads((tt/'test129.json').read_bytes())
  assert dm['passed'] and tm['passed'] and dm['one_step_cases']==26112 and dm['negative_error_code_rejected']
  for directory,data in [(dt,dm),(tt,tm)]:
   for n,h in data['sources'].items():assert sha(directory/n)==h,n
  assert 'PASS128 DIFF one_step_cases=26112' in (dt/'diff.log').read_text() and '** Fatal: DIFF128' in (dt/'negative.log').read_text()
  for n in ['nes_rom_loader.sv','nes_rom_boot.sv','nes_rom_physical.sv']:assert sha(dt/n)==sha(tt/n)==sha(ff/n),n
  experiments.append(dict(test=tn,diff=dn,fit=fn,one_step_cases=26112,adopted=False))
 meta=json.loads((f/'review129.json').read_bytes());core=inspect(f);assert {k:meta[k] for k in core}==core
 assert json.loads((f/'fit129.json').read_bytes())['phases']==[dict(phase=x,returncode=0) for x in ['map','fit','sta']]
 assert not re.search(r'^\s*set_(false_path|clock_groups|multicycle_path)',(f/'live.sdc').read_text(),re.M)
 rows=list(csv.DictReader((f/'reader129-paths.tsv').open(),delimiter='\t'))
 old=[x for x in rows if x['group']=='old_direct'];valid=[x for x in rows if x['group']=='valid_input']
 assert len(old)==len(valid)==3 and all(x['paths']=='0' for x in old+valid)
 owner=[x for x in rows if x['group'] in ['release_owner','owner_address','owner_input']]
 assert len(owner)==meta['reader_owner_paths']['owner_stage_paths']
 assert min(float(x['slack']) for x in owner)==meta['reader_owner_paths']['minimum_setup_ns']
 assert all(float(x['slack'])>=0 for x in owner)
 topology=list(csv.DictReader((f/'topology126.tsv').open(),delimiter='\t'));first=[x for x in topology if x['stage']=='0']
 assert len(first)==1 and first[0]['to'].endswith('release_reset[1]')
 times=list(csv.DictReader((f/'timing126.tsv').open(),delimiter='\t'));assert len(times)==6 and all(float(x['slack'])>=0 for x in times)
 return dict(final_fit=meta,seeded_images_bytes=[81920,98304],pin_writes_error_cases=87,check_reads=308,run_reads=128,write_fault_positions=86,check_cancel_reused=48,additional_cancel_cases=96,stopped_clock_cases=3,ready_misuse_cases=6,final_causal_rejections=2,unadopted_loader_experiments=experiments,full_image_writes_repeated=False,full_spi_cpu_session=False,installable=False)

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 m=json.loads((ROOT/'analysis/reader129-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 assert review(e)==m['checks'];print('PASS129 frozen source/test/fit identity; full IO and installation remain separate')
if __name__=='__main__':main()
