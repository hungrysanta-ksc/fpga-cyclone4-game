# SPDX-License-Identifier: MIT
"""Functional/source equality and full-board resource/timing/CDC inventory206."""
from pathlib import Path
import argparse,json,csv,re,collections
from nes_board204 import ROOT,BASE,sha
from nes_board206 import MODULES,transform
from nes_bulk194_evidence import verify_archive
from check_nes_boundary165 import measurements

FILES=['tools/nes_board206.py','tools/test_nes_board206.py','tools/test_nes_cancel206.py',
 'tests/nes-functional/cancel206_tb.sv','tools/nes_cdc206_inventory.tcl','tools/nes_board206_evidence.py','docs/nes-board206-contract.ko.md']
def read(p):return json.loads(p.read_bytes())
def rows(p):return list(csv.DictReader(p.open(),delimiter='\t'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-board206';prep=read(d/'source03/preparation206.json')
 for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
 for place in ['source03','mapfit01','timing01','io02']:
  for n,h in prep['sources'].items():
   if n=='board.qsf' and place in ['timing01','io02']:
    expected=(d/'source03'/n).read_text().replace('LAST_QUARTUS_VERSION "25.1std.0 Lite Edition"','LAST_QUARTUS_VERSION "25.1std.0 Standard Edition"')
    assert (d/place/n).read_text()==expected,(place,n)
   else:assert sha(d/place/n)==h,(place,n)
 for n,h in prep['sources'].items():
  if n!='board.qsf':assert sha(d/'source02'/n)==h,n
 for old,new in MODULES.items():assert (d/'source03'/new).read_text()==transform(old,(BASE/'probes/nes-board205/source01'/old).read_text())
 for name,tool in [('test01','test_nes_board206.py'),('cancel01','test_nes_cancel206.py')]:
  r=read(d/name/'result.json');assert r['passed'] and r['script_sha256']==sha(ROOT/'tools'/tool)
  for n,h in r['source_pins'].items():assert sha(BASE/n)==h,n
 t=read(d/'test01/result.json')
 for label in ['direct','atomic']:
  r=t['cases'][label];assert r['passed'] and r['script_sha256']==sha(d/'test01'/(label+'.py'))
  for n,h in r['source_pins'].items():assert sha(BASE/n)==h,n
 assert t['cases']['direct']['cases']==read(BASE/'probes/nes-board205/test01/result.json')['cases']
 assert t['cases']['atomic']['checks']==22 and read(d/'cancel01/result.json')['checks']==21
 assert t['cases']['loader']==dict(states=294912,sequences=1056,exhaustive=524288,wrong_terminal_rejected=True)
 for n in ['map','fit']:assert (d/'mapfit01'/(n+'.exitcode')).read_text()=='0'
 for n in ['nes_board204_timing','nes_cdc206_inventory','nes_board205_paths']:
  assert (d/'timing01'/(n+'.exitcode')).read_text()=='0'
  assert sha(d/'timing01'/(n+'.tcl'))==sha(ROOT/'tools'/(n+'.tcl'))
 summary=(d/'mapfit01/output_files/board.fit.summary').read_text();fit=(d/'mapfit01/output_files/board.fit.rpt').read_text(errors='replace')
 le=int(re.search(r'Total logic elements\s*:\s*([\d,]+)',summary)[1].replace(',',''))
 ff=int(re.search(r'Total registers\s*:\s*(\d+)',summary)[1])
 lab=int(re.search(r'Total LABs:.*?;\s*(\d+) / 963',fit)[1]);m9k=int(re.search(r'M9Ks\s*; (\d+) / 56',fit)[1])
 timing={}
 for view in ['nominal','implementation']:
  r=rows(d/'timing01'/(view+'-paths204.tsv'));assert len({x['corner'] for x in r})==3
  timing[view]={k:min([x for x in r if x['kind']==k and ((x['from_clock']=='nes')==(x['to_clock']=='nes'))],key=lambda x:float(x['slack'])) for k in ['setup','hold']}
 inv=rows(d/'timing01/inventory206.tsv');top=rows(d/'timing01/topology206.tsv')
 assert len({x['corner'] for x in inv})==3 and len(top)>0
 assert len(top)==len({x['first'] for x in top})
 for x in top:
  expected=x['first'].replace('epoch_meta','epoch_sync') if 'epoch_meta' in x['first'] else x['first'][:-3]+'[1]'
  assert x['fanout']==expected,x
 classifications=collections.Counter();classified=[];first={x['first'] for x in top};payload=[];gray=[]
 for x in inv:
  if ((x['from_clock']=='nes')==(x['to_clock']=='nes')):g='related_pll'
  elif x['kind'] in ['recovery','removal']:g='async_reset_review_open'
  elif x['to'] in first:
   g='gray_first_stage' if '|epoch_meta[' in x['to'] else 'control_first_stage'
   if g=='gray_first_stage' and x['kind']=='setup':gray.append(x)
  elif 'direct_path' in x['from'] and '|held[' in x['from'] and x['to']==x['from'].replace('|held[','|received['):
   g='new_held_payload_bounds_open'
   if x['kind']=='setup':payload.append(x)
  elif 'direct_path' in x['from'] or 'direct_path' in x['to']:g='new_other_review_open'
  else:g='inherited_unmodified'
  classifications[(x['corner'],x['kind'],g)]+=1;classified.append(dict(group=g,**x))
 assert not any(x['group']=='new_other_review_open' for x in classified)
 assert len(top)==45
 epoch_reset=[x for x in inv if x['kind'] in ['recovery','removal'] and float(x['slack'])<0 and
  'content_lifetime' in x['to'] and re.search(r'\|(epoch_meta|epoch_sync|previous)\[',x['to'])]
 assert len(epoch_reset)==288 and len({x['to'] for x in epoch_reset})==96
 assert (d/'io02/io.exitcode').read_text()=='0'
 assert sha(d/'io02/nes_boundary165_paths.tcl')==sha(ROOT/'tools/nes_boundary165_paths.tcl')
 io=measurements(d/'io02');assert io==read(d/'io02/result.json')
 assert io['conditional_data_bounds_pass'] and io['native_payload_reset_pass']
 io_public={n:sha(ROOT/n) for n in ['tools/check_nes_boundary165.py','tools/nes_boundary165_paths.tcl']}
 (a.out/'classified.json').write_text(json.dumps(classified,indent=2)+'\n',encoding='utf8',newline='\n')
 previous=read(ROOT/'analysis/board205-verification.json')
 for n,h in previous['source_pins'].items():assert sha(ROOT/n)==h,n
 archives=[verify_archive(x['name']) for x in previous['prior_archives']]+[verify_archive('nes-board205')]
 assert read(ROOT/'analysis/scroll193-measurement-plan.json')['collected_runs']==[]
 r=dict(passed=True,meaning='Evidence consistency and functional PASS; not deployment/physical CDC approval.',
  selected=['source03','test01','cancel01','mapfit01','timing01','io02'],source_pins={n:sha(ROOT/n) for n in FILES},prior_archives=archives,
  functional_frames=9,bytes=1968,same_fixture_cycles=True,partial_checks=22,cancel_checks=21,loader=t['cases']['loader'],
  fitted_le=le,registers=ff,lab=lab,m9k=m9k,le_spare=15408-le,lab_spare=963-lab,
  delta_from205=dict(le=le-15182,registers=ff-8337,lab=lab-961,m9k=m9k-47),fit_passed=True,timing=timing,
  cdc=dict(inventory_rows=len(inv),corners=3,verified_first_stage_single_fanouts=len(top),
   classifications=[dict(corner=c,kind=k,group=g,count=n) for (c,k,g),n in sorted(classifications.items())],
   held_payload_max_delay_ns=max(float(x['delay']) for x in payload),gray_max_delay_ns=max(float(x['delay']) for x in gray),
   unclassified_new_data_paths=0,epoch_payload_negative_recovery_rows=len(epoch_reset),epoch_payload_reset_registers=96,
   new_exceptions_added=False,all_corner_cdc_budgets_approved=False),io=io,io_public_sources=io_public,
  adopted=False,nominal_setup_passed=float(timing['nominal']['setup']['slack'])>=0,full_io_cdc_approved=False,new_package=False,
  actual_c_rtl_snes_cosim=False,physical=False,actual_scroll_measured=False,meets_60fps_budget=False,
  next='Retain206 passing related-clock placement; no loader/seed/refit loop. Local synchronous cold-reset release for source_epoch205 meta/sync/previous96 registers, preserving stopped-clock invalidate and stable epoch admission; classify reset release/held-data bound exactly. Then minimum actual board-C-SNES pair and FIRSTLEVELSCROLL, not isolated codec/boot repetition.')
 text=json.dumps(r,indent=2)+'\n';(a.out/'result.json').write_text(text,encoding='utf8',newline='\n');(ROOT/'analysis/board206-verification.json').write_text(text,encoding='utf8',newline='\n')
 print(json.dumps({k:r[k] for k in ['passed','fitted_le','registers','lab','m9k','delta_from205','timing','nominal_setup_passed']}))
if __name__=='__main__':main()
