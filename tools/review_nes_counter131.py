# SPDX-License-Identifier: MIT
"""Report131 fitted clock minima and the new diagnostic reset chain."""
from pathlib import Path
import argparse,csv,json,re,shutil,subprocess
from nes_loader127 import ROOT,put,sha
def inspect(o):
 report=(o/'output_files/live.fit.rpt').read_text(errors='replace')
 summary=(o/'output_files/live.fit.summary').read_text(errors='replace')
 assert 'Fitter Status : Successful' in summary
 def count(label):
  match=re.search(re.escape(label)+r'\s*[:;]\s*([\d,]+)',summary+'\n'+report);assert match,label
  return int(match[1].replace(',',''))
 resources={n:count(n) for n in ['Total logic elements','Total registers','Total pins','Total virtual pins','Total PLLs']}
 match=re.search(r'; Total LABs:  partially or completely used\s*;\s*([\d,]+) / 963',report);assert match
 resources['LAB']=int(match[1].replace(',',''));assert resources['LAB']<=963 and resources['Total logic elements']<=15408
 resources['M9K']=count('M9Ks')
 assert 'Ignored assignment' not in (o/'fit131.log').read_text(errors='replace')
 rows=list(csv.DictReader((o/'clock-pairs124.tsv').open(),delimiter='\t'))
 same={}
 for r in rows:
  if r['type']=='setup' and r['from_clock']==r['to_clock']:
   n=r['from_clock'];same[n]=min(same.get(n,1e9),float(r['slack']))
 assert len(same)==3,same
 raw=min(float(r['slack']) for r in rows)
 m=dict(resources=resources,same_clock_setup_min_ns=same,raw_clock_pair_min_ns=raw,clock_rows=len(rows),fit_passed=True,same_clock_setup_pass=all(v>=0 for v in same.values()),full_timing_pass=False,old126_data_constraints_reused=False,installable=False)
 hold={}
 for r in rows:
  if r['type']=='hold' and r['from_clock']==r['to_clock']:
   n=r['from_clock'];hold[n]=min(hold.get(n,1e9),float(r['slack']))
 assert len(hold)==3
 m['same_clock_hold_min_ns']=hold
 m['same_clock_hold_pass']=all(v>=0 for v in hold.values())
 return m
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--quartus-bin',type=Path,required=True);a=p.parse_args();o=a.out
 build=json.loads((o/'fit131.json').read_bytes());phases=build['phases']
 required=['fit','sta'] if build.get('refit_only') else ['map','fit','sta']
 assert phases==[dict(phase=n,returncode=0) for n in required], 'Wait for the complete build before running audit'
 # Existing read-only audit selects clocks and local_memory, no old reader hierarchy.
 shutil.copy2(ROOT/'tools/nes_reset124_audit.tcl',o/'audit131.tcl')
 with (o/'audit131.log').open('wb') as log:r=subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t','audit131.tcl'],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 assert r.returncode==0
 # Exact new chain; no obsolete126 reader hierarchy is used.
 put(o/'chains126.tcl','set chains126 {{release diagnostic {nes_domain_reset124:diagnostic_release|release_reset[0]} {nes_domain_reset124:diagnostic_release|release_reset[1]}}}\n')
 shutil.copy2(ROOT/'tools/nes_control126.tcl',o/'reset131.tcl')
 with (o/'reset131.log').open('wb') as log:r=subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t','reset131.tcl'],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 assert r.returncode==0
 topology=list(csv.DictReader((o/'topology126.tsv').open(),delimiter='\t'))
 first=[x for x in topology if x['stage']=='0'];assert len(first)==1 and first[0]['to'].endswith('release_reset[1]')
 timing=list(csv.DictReader((o/'timing126.tsv').open(),delimiter='\t'));assert len(timing)==6 and all(float(x['slack'])>=0 for x in timing)
 local=list(csv.DictReader((o/'local-reset126.tsv').open(),delimiter='\t'));assert local
 result=inspect(o);result['diagnostic_reset_chain']=dict(first_stage_fanout=1,stage_paths=6,min_stage_slack_ns=min(float(x['slack']) for x in timing),local_release_paths=len(local),min_local_release_slack_ns=min(float(x['slack']) for x in local))
 shutil.copy2(ROOT/'tools/nes_reader129_paths.tcl',o/'reader131-paths.tcl')
 with (o/'reader131-paths.log').open('wb') as log:r=subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t','reader131-paths.tcl'],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 assert r.returncode==0
 rows=list(csv.DictReader((o/'reader129-paths.tsv').open(),delimiter='\t'))
 old=[x for x in rows if x['group']=='old_direct'];assert len(old)==3 and all(x['paths']=='0' for x in old)
 valid=[x for x in rows if x['group']=='valid_input'];assert len(valid)==3 and all(x['paths']=='0' for x in valid)
 owner=[x for x in rows if x['group'] in ['release_owner','owner_address','owner_input']];assert owner and all(x['slack']!='-' for x in owner)
 result['reader_owner_paths']=dict(old_direct_paths=0,owner_stage_paths=len(owner),minimum_setup_ns=min(float(x['slack']) for x in owner),valid_register_setup_paths=0)
 shutil.copy2(ROOT/'tools/nes_counter131_paths.tcl',o/'state131.tcl')
 with (o/'state131.log').open('wb') as log:r=subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t','state131.tcl'],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 assert r.returncode==0
 edges=list(csv.DictReader((o/'state131-edges.tsv').open(),delimiter='\t'))
 assert len({x['register'] for x in edges})==16
 enables=[x for x in edges if x['source'].endswith('|ena')]
 state_enables=[x for x in enables if '|state.' in x['register']]
 assert not state_enables,'State enable inference still active'
 state_sync=[x for x in edges if '|state.' in x['register'] and x['source'].endswith(('|sload','|sclr'))]
 if 'ALLOW_SYNCH_CTRL_USAGE OFF' in (o/'nes_rom_loader.sv').read_text():
  assert not state_sync,'State synchronous load/clear still present'
 # Only state has the attribute in the selected candidate. Counter enables
 # remain observable; the dual-attribute experiment is explicitly unadopted.
 paths=list(csv.DictReader((o/'state131-timing.tsv').open(),delimiter='\t'))
 result['loader_ports']=dict(registers=16,enable_inputs=len(enables),state_enable_inputs=len(state_enables),state_sync_control_inputs=len(state_sync),reported_paths=len(paths),minimum_setup_ns=min(float(x['slack']) for x in paths if x['type']=='setup'),minimum_hold_ns=min(float(x['slack']) for x in paths if x['type']=='hold'))
 dependencies=list(csv.DictReader((o/'counter131-dependencies.tsv').open(),delimiter='\t'))
 old=[x for x in dependencies if x['group']=='loaded_count']
 assert len(old)==3 and all(x['paths']=='0' for x in old),'Byte-count acceptance still gates the timer'
 failed=[x for x in dependencies if x['group']=='check_failed']
 assert len(failed)==3 and all(x['paths']=='1' for x in failed)
 result['counter_dependencies']=dict(loaded_count_paths=0,check_failed_minimum_setup_ns=min(float(x['slack']) for x in failed))
 index=list(csv.DictReader((o/'index131-edges.tsv').open(),delimiter='\t'))
 assert len({x['register'] for x in index})==17
 assert not [x for x in index if x['source'].endswith('|ena')],'CHECK index enable still present'
 result['check_index_ports']=dict(registers=17,enable_inputs=0)
 address=list(csv.DictReader((o/'address131-edges.tsv').open(),delimiter='\t'))
 address_registers=len({x['register'] for x in address});assert 0<address_registers<=22
 assert not [x for x in address if x['source'].endswith(('|ena','|sload','|sclr'))],'Address control ports still present'
 result['load_address_ports']=dict(registers=address_registers,enable_inputs=0,sync_control_inputs=0)
 checked=list(csv.DictReader((o/'checked131-edges.tsv').open(),delimiter='\t'))
 assert len({x['register'] for x in checked})==8
 # fit05 retains eight enable pins despite the source attribute. Record the
 # actual mapped result; do not claim the option guarantees their removal.
 checked_enable=[x for x in checked if x['source'].endswith('|ena')]
 assert len(checked_enable)==8
 assert not [x for x in checked if x['source'].endswith(('|sload','|sclr'))]
 result['checked_data_ports']=dict(registers=8,enable_inputs=8,sync_control_inputs=0,enable_removal_claim=False)
 put(o/'review131.json',json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
