# SPDX-License-Identifier: MIT
"""Recompute132 current routing/CDC scope and retain unresolved crossings."""
from pathlib import Path
import argparse,json,re
from nes_cdc132_sta import ROOT,sha,rows,inventory,BUDGETS,PERIODS,CONTROL

def review(e):
 f=e/'sta02';t=e/'protocol01';xs,groups=inventory(f/'inventory132.tsv')
 meta=json.loads((f/'sta132.json').read_bytes());p=json.loads((t/'protocol132.json').read_bytes())
 assert meta['passed'] and p['passed'] and not meta['new_fit']
 assert not any(meta[k] for k in ['full_timing_pass','mtbf_signoff','external_io_signoff','installable'])
 b=e.parents[1];a131=b/'nes-counter131/evidence';a125=b/'nes-cdc125/evidence'
 for tag,a in [('counter131',a131),('cdc125',a125)]:
  old=json.loads((ROOT/f'analysis/{tag}-verification.json').read_bytes());assert sha(a/'manifest.json')==old['manifest_sha256']
 p131=json.loads((a131/'manifest.json').read_bytes())['files'];p125=json.loads((a125/'manifest.json').read_bytes())['files']
 inputs=json.loads((f/'inputs132.json').read_bytes());changed=[]
 assert inputs['source_manifest']==sha(a131/'manifest.json')
 assert not inputs['new_fit'] and not inputs['new_map']
 for n,h in inputs['files'].items():
  assert h==p131['fit05/'+n]==sha(a131/'fit05'/n),n
  if sha(f/n)!=h:changed.append(n)
 assert sorted(changed)==['db/live.cycloneive_io_sim_cache.31um_ss_1200mv_85c_slow.hsd','db/live.taw.rdb']
 # Only STA timing/IO-model caches differ; all routed/source/SDC/QSF inputs match.
 for name,tool in [('executed-sta132.py','nes_cdc132_sta.py'),('executed-inventory132.py','nes_cdc132_inventory.py')]:assert sha(f/name)==sha(ROOT/'tools'/tool)
 assert sha(t/'executed-protocol132.py')==sha(ROOT/'tools/nes_cdc132_protocol.py')
 for n,h in p['sources'].items():assert sha(t/n)==h,n
 for n,h in p['inputs'].items():
  tag,key=n.split('/',1);ar,ps=(a131,p131) if tag=='counter131' else (a125,p125)
  assert h==ps[key]==sha(ar/key)
 assert sha(t/'nes_rom_physical.sv')==sha(f/'nes_rom_physical.sv')
 for n,h in p['bridge_reused'].items():assert h==sha(f/n)==p125['protocol01/'+n]==sha(a125/'protocol01'/n)
 assert p['bridge_result_sha256']==p125['protocol01/result125.json']==sha(a125/'protocol01/result125.json')
 assert json.loads((a125/'protocol01/result125.json').read_bytes())['passed']
 for name in ['reader-0','reader-3500']:
  log=(t/(name+'.log')).read_text();assert '** Fatal:' not in log and 'completed=525 canceled=13' in log
  match=re.search(r'CDC132 reader address=([0-9.]+) data=([0-9.]+)',log);assert match
  assert float(match[1])>=2*PERIODS['reader_address'] and float(match[2])>=2*PERIODS['reader_data']
 assert '** Fatal: CDC125 reader address age' in (t/'reader-early.log').read_text()
 assert 'PASS PHYSICAL' not in (t/'reader-early.log').read_text()
 assert (t/'reader-early.sv').read_text()==(t/'nes_rom_physical.sv').read_text().replace('request_sync[1]!=ack_toggle','request_sync[0]!=ack_toggle')
 constrained=rows(f/'constrained132.tsv');sdc=(f/'bundled132.sdc').read_text()
 assert 'set_false_path' not in sdc and 'set_clock_groups' not in sdc
 assert len(constrained)==1113 and sdc.count('set_max_delay ')==371
 for g,rs in groups.items():
  spec=meta['groups'][g];pairs={(x['from'],x['to']) for x in rs}
  assert spec['pairs']==len(pairs) and spec['rows']==len(rs)
  assert spec['max_data_delay_ns']==max(float(x['delay']) for x in rs)
  assert spec['raw_min_slack_ns']==min(float(x['slack']) for x in rs)
  if g not in BUDGETS:
   assert not any(x['group']==g for x in constrained);continue
  out=[x for x in constrained if x['group']==g]
  assert len(out)==3*len(pairs) and {(x['from'],x['to']) for x in out}==pairs
  for s,d in pairs:assert f'set_max_delay -from [exact132 {{{s}}}] -to [exact132 {{{d}}}] {PERIODS[g]}' in sdc
  assert spec['max_data_delay_ns']<BUDGETS[g] and min(float(x['slack']) for x in out)==spec['constrained_min_slack_ns']>0
 chains=rows(f/'chains132.tsv');top=rows(f/'topology132.tsv');tim=rows(f/'timing132.tsv');local=rows(f/'local-reset132.tsv')
 assert len(chains)==16 and {x['first'] for x in chains if x['kind']=='control'}==CONTROL
 assert len(tim)==96 and min(float(x['slack']) for x in tim)>0
 for x in chains:
  first=[r for r in top if r['chain']==x['chain'] and r['stage']=='0'];assert len(first)==1 and first[0]['to']==x['second']
 reset_pins={x[k] for x in chains if x['kind']=='release' for k in ['first','second']}
 negative=[x for x in local if float(x['slack'])<0]
 ordinary=[x for x in local if x['to'] not in reset_pins]
 assert len(local)==6492 and len(negative)==107 and all(x['to'] in reset_pins for x in negative)
 assert len(ordinary)==6168 and min(float(x['slack']) for x in ordinary)==0.498
 assert min(float(x['slack']) for x in local)==meta['local_reset_min_ns']==-4.601
 for report in f.glob('metastability-*.rpt'):assert "Design MTBF is not calculated" in report.read_text(errors='replace')
 io=(f/'unconstrained132.rpt').read_text()
 for key,count in [('Unconstrained Input Ports',83),('Unconstrained Output Ports',227)]:assert re.search(re.escape(key)+r'\s*;\s*'+str(count)+r'\s*;',io)
 # Preserve pre-existing124 discrepancy as rejected input, never repair old archive.
 fail=json.loads((e/'preflight/rejected124.json').read_bytes())
 assert sha(e/'preflight/observed124-manifest.json')==fail['observed']!=fail['expected']
 assert fail['expected']==json.loads((ROOT/'analysis/reset124-verification.json').read_bytes())['manifest_sha256']
 return dict(sta=meta,reader_reads=1050,reader_cancels=26,reader_phases_ps=[0,3500],early_capture_rejected=True,bridge125_exact_reused=True,sta_cache_changes=changed,reset_negative_rows=107,reset_negative_only_at_release_chain_inputs=True,non_chain_reset_rows=6168,non_chain_reset_min_ns=0.498,external_unconstrained_ports={'input':83,'output':227},rejected124=fail,physical_trial=False,installable=False)

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence
 m=json.loads((ROOT/'analysis/cdc132-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 assert review(e)==m['checks'];print('PASS132 frozen current371 pairs/16 chains/reader; lifecycle/config/IO remain open')
if __name__=='__main__':main()
