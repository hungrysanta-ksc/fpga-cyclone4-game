# SPDX-License-Identifier: MIT
"""Verify actual fitted chain topology and bounded data after QSF-only change."""
from pathlib import Path
import argparse,csv,json,re
from nes_cdc125_sta import ROOT,sha,inventory,BUDGETS,PERIODS
from verify_nes_reset124 import inspect_fit

def rows(p):return list(csv.DictReader(p.open(),delimiter='\t'))

def meta_chains(p):
 text=p.read_text()
 assert "Design MTBF is not calculated because the design doesn't meet its timing requirements." in text
 found={}
 for block in re.split(r'Synchronizer Chain #\d+:',text)[1:]:
  def field(k):return re.search('; '+re.escape(k)+r'\s*;\s*(.*?)\s*;',block)[1]
  first=field('Synchronization Node')
  found[first]=dict(method=field('Method of Synchronizer Identification'),length=int(field('Number of Synchronization Registers in Chain')),settling_ns=float(field('Available Settling Time (ns)')),included=field('Included in Design MTBF'),source=field('Source Node'))
 return found

def inspect(e):
 r=json.loads((e/'result126.json').read_bytes());assert r['tool_phases_passed']
 assert not any(r[k] for k in ['rtl_changed','map_rerun','full_timing_pass','mtbf_signoff','installable'])
 base=e/'baseline';new=e/'candidate'
 assert sha(e/'executed-control126.py')==sha(ROOT/'tools/nes_control126.py')
 for o in [base,new]:assert sha(o/'control126.tcl')==sha(ROOT/'tools/nes_control126.tcl')
 assert (new/'live.qsf').read_text()==(base/'live.qsf').read_text()+'\n# Exact four bridge chains; both registers must be marked.\n'+'\n'.join(r['assignments'])+'\n'
 assert len(r['assignments'])==8 and len(set(r['assignments']))==8
 assert sha(new/'synchronizers126.qsf')==sha(ROOT/'src/nes/diagnostic/nes_bridge_sync126.qsf')
 expected=[]
 for kind,name,first,second in r['chains']:
  if kind=='control' and 'nes_packet_cdc_ram:bridge|' in first:
   for node in [first,second]:expected.append('set_instance_assignment -name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS -to '+'|'.join(x.split(':')[-1] for x in node.split('|')))
 assert r['assignments']==expected
 sourcepins=json.loads((base/'result.json').read_bytes())['sources']
 for n,h in sourcepins.items():assert sha(base/n)==sha(new/n)==h,n
 chains=r['chains'];assert len(chains)==10
 summaries={}
 for label,o in [('baseline',base),('candidate',new)]:
  topo=rows(o/'topology126.tsv');tim=rows(o/'timing126.tsv');assert len(tim)==60
  assert len({x['corner'] for x in tim})==3
  local=rows(o/'local-reset126.tsv');assert local and min(float(x['slack']) for x in local)>0
  reports={f.stem:meta_chains(f) for f in o.glob('metastability-*.rpt')};assert len(reports)==3
  current=[]
  for kind,name,first,second in chains:
   f=[x for x in topo if x['from']==first];assert len(f)==1 and f[0]['to']==second,(label,first,f)
   ts=[x for x in tim if x['chain']==name];assert len(ts)==6
   assert all(x['from']==first and x['to']==second and float(x['slack'])>0 for x in ts)
   ms=[v[first] for v in reports.values()]
   is_bridge=kind=='control' and 'nes_packet_cdc_ram:bridge|' in first
   method='Automatic' if label=='baseline' and is_bridge else 'User Specified'
   included='No' if label=='baseline' and is_bridge else 'Yes'
   assert all(v['length']==2 and v['method']==method and v['included']==included for v in ms),(label,first,ms)
   current.append(dict(kind=kind,name=first,first_fanout=1,setup_min_ns=min(float(x['slack']) for x in ts if x['type']=='setup'),hold_min_ns=min(float(x['slack']) for x in ts if x['type']=='hold'),tool_settling_min_ns=min(v['settling_ns'] for v in ms),method=method,mtbf_inclusion_flag=included))
  summaries[label]=dict(chains=current,local_reset_rows=len(local),local_reset_min_ns=min(float(x['slack']) for x in local))
 raw,groups=inventory(new/'inventory125.tsv');bounded=rows(new/'constrained125.tsv');assert len(bounded)==1116
 data={}
 for g,budget in BUDGETS.items():
  xs=groups[g];ys=[x for x in bounded if x['group']==g]
  pairs={(x['from'],x['to']) for x in xs};assert {(x['from'],x['to']) for x in ys}==pairs and len(ys)==3*len(pairs)
  delay=max(float(x['delay']) for x in xs);slack=min(float(x['slack']) for x in ys)
  assert delay<budget<PERIODS[g] and slack>0
  data[g]=dict(pairs=len(pairs),max_data_delay_ns=delay,raw_budget_ns=budget,sdc_max_delay_ns=PERIODS[g],min_slack_ns=slack)
 fit=inspect_fit(new)
 # Audit124 is explicitly rerun on candidate; its historical result.json is
 # used only for unchanged source/pin identities, not new phase/timing results.
 for n in ['fit126.log','sta126.log','control126.log','audit126.log','inventory125.log','constraints125.log']:
  text=(new/n).read_text(errors='replace');assert 'was successful. 0 errors' in text,n
 assert 'Ignored assignment' not in (new/'fit126.log').read_text()
 assert (new/'audit124.tcl').read_bytes()==(ROOT/'tools/nes_reset124_audit.tcl').read_bytes()
 # Physical packing may alter LE use without changing mapped logic/registers.
 assert fit['LE']<=15408 and fit['LAB']<=963 and fit['M9K']==26 and fit['physical_pins']==46
 return dict(topology=summaries,fit=fit,data=data,raw_cross_min_ns=min(float(x['slack']) for x in raw),rtl_source_count=len(sourcepins),qsf_assignments=8,mtbf_calculated=False)

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence
 m=json.loads((ROOT/'analysis/control126-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for n,h in m['reused125'].items():assert sha(e/'fit02/candidate'/n)==h,n
 assert sha(e/'fit02/executed-review126.py')==sha(ROOT/'tools/review_nes_control126.py')
 assert inspect(e/'fit02')==m['checks']
 # First attempt built successfully but the assignments were ignored; rejected
 # by actual metadata comparison, never accepted as a fitted synchronizer fix.
 failed=e/'fit01/candidate'
 assert (failed/'fit126.log').read_text().count('Ignored assignment ANALYZE_METASTABILITY')==8
 for report in failed.glob('metastability-*.rpt'):
  found=meta_chains(report)
  assert all(found[x['name']]['method']=='Automatic' for x in m['checks']['topology']['candidate']['chains'] if 'nes_packet_cdc_ram:bridge|' in x['name'])
 print('PASS126 four bridge chains explicitly identified/refitted; six controls/four releases/372 bundled pairs pass scoped checks; no MTBF/IO/RUN signoff')
if __name__=='__main__':main()
