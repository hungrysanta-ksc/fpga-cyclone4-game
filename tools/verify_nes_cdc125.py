# SPDX-License-Identifier: MIT
"""Verify frozen125 raw evidence without rerunning synthesis or simulation."""
from pathlib import Path
import argparse,ast,csv,json,re
from nes_cdc125_sta import ROOT,sha,inventory,BUDGETS,PERIODS

def inspect(e):
 s=e/'sta03';p=e/'protocol01'
 r=json.loads((s/'result125.json').read_bytes());q=json.loads((p/'result125.json').read_bytes())
 assert r['passed'] and q['passed']
 rows,groups=inventory(s/'inventory125.tsv')
 bounded=list(csv.DictReader((s/'constrained125.tsv').open(),delimiter='\t'))
 assert len(bounded)==1116 and len({(x['from'],x['to']) for x in bounded})==372
 assert len({x['corner'] for x in bounded})==3
 assert r['raw_min_slack_ns']==min(float(x['slack']) for x in rows)
 expected=[]
 for g,budget in BUDGETS.items():
  xs=groups[g];ps={(x['from'],x['to']) for x in xs};ys=[x for x in bounded if x['group']==g]
  assert {(x['from'],x['to']) for x in ys}==ps and len(ys)==len(ps)*3
  v=r['groups'][g]
  assert v['budget_ns']==budget<PERIODS[g]==v['sdc_max_delay_ns']==v['destination_period_ns']
  assert v['conditional_capture_min_ns']==2*PERIODS[g]
  assert v['max_data_delay_ns']==max(float(x['delay']) for x in xs)<budget
  assert v['constrained_min_slack_ns']==min(float(x['slack']) for x in ys)>0
  for src,dst in ps:expected.append(f'set_max_delay -from [exact125 {{{src}}}] -to [exact125 {{{dst}}}] {PERIODS[g]}')
 actual=[x for x in (s/'bundled125.sdc').read_text().splitlines() if x.startswith('set_max_delay')]
 assert sorted(actual)==sorted(expected)
 for n in ['live.sdc','bundled125.sdc']:
  text=(s/n).read_text();assert 'set_false_path' not in text and 'set_clock_groups' not in text
 assert len(r['unexcepted_controls'])==18 and r['unexcepted_controls']==groups['control_first_stage']
 assert all(not r[k] for k in ['full_timing_pass','external_io_signoff','installable'])
 failed=list(csv.DictReader((e/'sta02/constrained125.tsv').open(),delimiter='\t'))
 assert min(float(x['slack']) for x in failed)==-0.175
 assert (e/'sta02/inventory125.tsv').read_bytes()==(s/'inventory125.tsv').read_bytes()
 assert len(q['runs'])==7 and sum(x['negative'] for x in q['runs'].values())==2
 summaries={}
 for label,run in q['runs'].items():
  log=(p/(label+'.log')).read_text();assert run['passed']
  assert run['summary']==[x for x in log.splitlines() if 'CDC125' in x or 'PASS PHYSICAL' in x or 'PASS NES PACKET CDC' in x]
  if run['negative']:assert '** Fatal: CDC125' in log
  else:
   assert '** Fatal:' not in log
   if label.startswith('reader'):
    m=re.search(r'address=([\d.]+) data=([\d.]+) checks=(\d+)/(\d+) hold=(\d+)',log)
    assert m and float(m[1])>=11.902 and float(m[2])>=90.906
    assert int(m[3])==537 and int(m[4])==525 and int(m[5])>=1036
   else:
    m=re.search(r'request=([\d.]+) reply=([\d.]+) checks=(\d+)/(\d+) hold=(\d+)',log)
    assert m and float(m[1])>=90.906 and float(m[2])>=23.806
    assert int(m[3])==int(m[4])==6427 and int(m[5])==12847
   summaries[label]=run['summary']
 for n,h in q['sources'].items():assert sha(p/n)==h,n
 old=json.loads((ROOT/'analysis/reset124-verification.json').read_bytes())
 oldpins=json.loads((e/'baseline124-manifest.json').read_bytes())['files']
 assert sha(e/'baseline124-manifest.json')==old['manifest_sha256']
 for n,h in q['inputs'].items():assert oldpins[n]==h,n
 for n in ['nes_rom_physical.sv','nes_packet_cdc_ram.sv','nes_packet_queue_ram.sv']:
  assert sha(p/n)==sha(s/n)==oldpins['fit01/'+n]
 db_changed=[n for n,h in oldpins.items() if n.startswith(('fit01/db/','fit01/incremental_db/')) and sha(s/n[len('fit01/'):])!=h]
 # TimeQuest updates its own timing-analysis database; routed fit DBs stay exact.
 assert db_changed==['fit01/db/live.taw.rdb'],db_changed
 assert sha(s/'executed-sta125.py')==sha(ROOT/'tools/nes_cdc125_sta.py')
 assert sha(s/'inventory125.tcl')==sha(ROOT/'tools/nes_cdc125_inventory.tcl')
 assert sha(p/'executed-protocol125.py')==sha(ROOT/'tools/nes_cdc125_protocol.py')
 # Protocol01 imported only these helpers from the earlier STA02 revision.
 def helpers(path):
  return [ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ['sha','put']]
 assert helpers(e/'sta02/executed-sta125.py')==helpers(ROOT/'tools/nes_cdc125_sta.py')
 for kind in ['reader','bridge']:assert sha(p/f'cdc125_{kind}.svh')==sha(ROOT/f'tests/nes-functional/cdc125_{kind}.svh')
 return dict(groups=r['groups'],raw_rows=len(rows),data_pairs=372,control_pairs=6,constrained_rows=len(bounded),raw_min_slack_ns=r['raw_min_slack_ns'],protocol=summaries,negative_controls=2)

def main():
 a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);e=a.parse_args().evidence
 m=json.loads((ROOT/'analysis/cdc125-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 assert inspect(e)==m['checks']
 print('PASS125 exact372 bundled pairs/3corners; 5 protocol runs/2 early-use rejections; first-stage/reset/IO remain OPEN')
if __name__=='__main__':main()
