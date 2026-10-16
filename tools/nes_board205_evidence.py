# SPDX-License-Identifier: MIT
"""205 functional/fit/timing and routed CDC inventory; no signoff by tool exit0."""
from pathlib import Path
import argparse,json,csv,re,collections
from nes_board204 import ROOT,BASE,sha
from nes_bulk194_evidence import verify_archive
FILES=['src/nes/rtl/nes_source_epoch205.sv','src/nes/rtl/nes_tile205.sv',
 'tests/nes-functional/source_epoch205_tb.sv','tests/nes-functional/tile_stream205_tb.sv',
 'tools/nes_board205.py','tools/test_nes_board205.py','tools/test_nes_epoch205.py',
 'tools/test_nes_stream205.py','tools/nes_cdc205_inventory.tcl','tools/nes_board205_paths.tcl',
 'tools/nes_board205_evidence.py','docs/nes-board205-contract.ko.md']
def read(p):return json.loads(p.read_bytes())
def rows(p):return list(csv.DictReader(p.open(),delimiter='\t'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-board205';prep=read(d/'source01/preparation205.json')
 for name in ['source01','mapfit01','timing01','inventory02','paths02']:
  for n,h in prep['sources'].items():
   if n=='board.qsf' and name not in ['source01','mapfit01']:
    expected=(d/'source01'/n).read_text().replace('LAST_QUARTUS_VERSION "25.1std.0 Lite Edition"','LAST_QUARTUS_VERSION "25.1std.0 Standard Edition"')
    assert (d/name/n).read_text()==expected,(name,n)
   else:assert sha(d/name/n)==h,(name,n)
 for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
 for name,tool in [('test01','test_nes_board205.py'),('test01/atomic','test_nes_stream205.py'),('epoch01','test_nes_epoch205.py')]:
  r=read(d/name/'result.json');assert r['passed'] and r['script_sha256']==sha(ROOT/'tools'/tool)
  for n,h in r['source_pins'].items():assert sha(BASE/n)==h,n
 test=read(d/'test01/result.json');old=read(BASE/'probes/nes-board204/test01/result.json')
 assert test['cases']==old['cases'] and sum(x['bytes'] for x in test['cases'])==1968
 assert read(d/'epoch01/result.json')['checks']==20 and read(d/'test01/atomic/result.json')['checks']==22
 for n in ['map','fit']:assert (d/'mapfit01'/(n+'.exitcode')).read_text()=='0'
 for n in ['nes_board204_timing','nes_cdc205_inventory','nes_board204_paths']:
  assert (d/'timing01'/(n+'.exitcode')).read_text()=='0'
 assert (d/'inventory02/inventory.exitcode').read_text()=='0' and (d/'paths02/paths205.exitcode').read_text()=='0'
 assert sha(d/'inventory02/nes_cdc205_inventory.tcl')==sha(ROOT/'tools/nes_cdc205_inventory.tcl')
 assert sha(d/'paths02/nes_board205_paths.tcl')==sha(ROOT/'tools/nes_board205_paths.tcl')
 fit=(d/'mapfit01/output_files/board.fit.rpt').read_text(errors='replace')
 assert re.search(r'Total LABs:.*?961 / 963',fit) and re.search(r'M9Ks\s*; 47 / 56',fit)
 assert '15,182 / 15,408' in (d/'mapfit01/output_files/board.fit.summary').read_text()
 assert '8337' in (d/'mapfit01/output_files/board.fit.summary').read_text()
 timing={}
 for view in ['nominal','implementation']:
  r=rows(d/'timing01'/(view+'-paths204.tsv'));assert len({x['corner'] for x in r})==3
  timing[view]={k:min([x for x in r if x['kind']==k and ((x['from_clock']=='nes')==(x['to_clock']=='nes'))],key=lambda x:float(x['slack'])) for k in ['setup','hold']}
 assert float(timing['nominal']['setup']['slack'])==-0.739 and float(timing['nominal']['hold']['slack'])==0.148
 assert 'Worst case slack is 0.240' in (d/'timing01/paths204-0-check.rpt').read_text()
 for i in range(3):assert 'Nothing to report.' in (d/'timing01'/f'paths204-{i}-epoch-status.rpt').read_text()
 # Enumerate all cross-clock paths, including unchanged paths and recovery/removal.
 inv=rows(d/'inventory02/inventory205.tsv');top=rows(d/'inventory02/topology205.tsv')
 assert len(inv)==18582 and len(top)==44 and len({x['first'] for x in top})==44
 for x in top:
  expected=x['first'].replace('epoch_meta','epoch_sync') if 'epoch_meta' in x['first'] else x['first'][:-3]+'[1]'
  assert x['fanout']==expected,x
 ep=[x for x in inv if 'content_lifetime' in x['from'] or 'content_lifetime' in x['to']]
 epdata=[x for x in ep if x['kind'] in ['setup','hold']]
 assert len(epdata)==64
 for x in epdata:
  assert '|gray[' in x['from'] and x['to']==x['from'].replace('|gray[','|epoch_meta['),x
 classifications=collections.Counter();classified=[]
 for x in inv:
  if ((x['from_clock']=='nes')==(x['to_clock']=='nes')):g='related_pll'
  elif x['kind'] in ['recovery','removal']:g='async_reset_review_open'
  elif any(x['to']==t['first'] for t in top):g='gray_first_stage' if '|epoch_meta[' in x['to'] else 'control_first_stage'
  elif 'direct_path' in x['from'] and '|held[' in x['from'] and x['to']==x['from'].replace('|held[','|received['):g='new_held_payload_bounds_open'
  elif 'direct_path' in x['from'] or 'direct_path' in x['to']:g='new_cancel_or_other_review_open'
  else:g='inherited_unmodified'
  classifications[(x['kind'],g)]+=1;classified.append(dict(group=g,**x))
 (a.out/'classified.json').write_text(json.dumps(classified,indent=2)+'\n',encoding='utf8')
 previous=read(ROOT/'analysis/board204-verification.json')
 for n,h in previous['source_pins'].items():assert sha(ROOT/n)==h,n
 archives=[verify_archive(x['name']) for x in previous['prior_archives']]+[verify_archive('nes-board204')]
 assert read(ROOT/'analysis/scroll193-measurement-plan.json')['collected_runs']==[]
 r=dict(passed=True,meaning='Evidence consistency and functional PASS; NOT FPGA timing/CDC approval.',
  selected=['source01','epoch01','test01','test01/atomic','mapfit01','timing01','inventory02','paths02'],
  source_pins={n:sha(ROOT/n) for n in FILES},prior_archives=archives,
  functional_frames=9,bytes=1968,epoch_checks=20,partial_fault_and_recovery_checks=22,same_fixture_cycles=True,
  fitted_le=15182,registers=8337,lab=961,m9k=47,le_spare=226,lab_spare=2,
  delta_from204=dict(le=-128,registers=-249,lab=-2,m9k=0),fit_passed=True,timing=timing,
  prior_check_path_slack_ns=0.240,old_raw_status_bypass_absent=True,
  cdc=dict(inventory_rows=len(inv),verified_first_stage_single_fanouts=44,gray_bits=32,
   classifications=[dict(kind=k,group=g,count=n) for (k,g),n in sorted(classifications.items())],
   topology_and_default_corner_inventory_only=True,new_exceptions_added=False,all_corner_cdc_budgets_approved=False),
  adopted=False,nominal_setup_passed=False,full_io_cdc_approved=False,new_package=False,actual_c_rtl_snes_cosim=False,
  physical=False,actual_scroll_measured=False,meets_60fps_budget=False,
  next='Retain205 local status and single-byte stream. Resolve explicit new CDC held-data/cancel/reset boundaries; inspect completion predicate9LUT/67%routing and source-count fanout together with small RAM cache/state storage budget. Do not undo safety, grow clocks, repeat seeds or restart isolated loader microFIT. Then full timing/IO and board-C-SNES pair before FIRSTLEVELSCROLL.')
 text=json.dumps(r,indent=2)+'\n';(a.out/'result.json').write_text(text,encoding='utf8');(ROOT/'analysis/board205-verification.json').write_text(text,encoding='utf8')
 print(json.dumps(dict(passed=True,le=15182,lab=961,registers=8337,setup=-0.739,old_bypass_absent=True,prior_archives=len(archives),classifications=r['cdc']['classifications'])))
if __name__=='__main__':main()
