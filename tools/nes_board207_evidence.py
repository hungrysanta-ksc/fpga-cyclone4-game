# SPDX-License-Identifier: MIT
"""Pin both207 reset candidates, exact96-register reset paths and board results.
Evidence consistency PASS is separate from candidate timing/deployment approval.
"""
from pathlib import Path
import argparse,json,csv,re,collections
from nes_board204 import ROOT,BASE,sha
from nes_bulk194_evidence import verify_archive
from check_nes_boundary165 import measurements

FILES=['tools/nes_board207.py','tools/nes_board207_shared.py',
 'tools/test_nes_epoch207.py','tools/test_nes_epoch207_shared.py',
 'tools/nes_reset207_paths.tcl','tools/nes_reset207_shared_paths.tcl',
 'tools/nes_board207_evidence.py','docs/nes-board207-contract.ko.md']

def read(p):return json.loads(p.read_bytes())
def rows(p):return list(csv.DictReader(p.open(),delimiter='\t'))

def candidate(d,index):
 suffix=f'{index:02d}';src=d/('source'+suffix);tim=d/('timing'+suffix)
 prep=read(src/'preparation207.json')
 for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
 for place in ['source','mapfit','timing','io']:
  for n,h in prep['sources'].items():
   if n=='board.qsf' and place in ['timing','io']:
    expected=(src/n).read_text().replace('LAST_QUARTUS_VERSION "25.1std.0 Lite Edition"','LAST_QUARTUS_VERSION "25.1std.0 Standard Edition"')
    assert (d/(place+suffix)/n).read_text()==expected,(place,n)
   else:assert sha(d/(place+suffix)/n)==h,(place,n)
 test=read(d/('epoch'+suffix)/'result.json')
 tool='test_nes_epoch207.py' if index==1 else 'test_nes_epoch207_shared.py'
 assert test['passed'] and test['script_sha256']==sha(ROOT/'tools'/tool)
 for n,h in test['source_pins'].items():assert sha(BASE/n)==h,n
 assert test['baseline_checks']==20 and test['cold_cases']==32 and test['wrong_admission_rejected']
 if index==2:assert sha(d/'epoch02/runner.py')==test['runner_sha256']
 for n in ['map','fit']:assert (d/('mapfit'+suffix)/(n+'.exitcode')).read_text()=='0'
 resettool='nes_reset207_paths' if index==1 else 'nes_reset207_shared_paths'
 for n in ['nes_board204_timing','nes_cdc206_inventory','nes_board205_paths',resettool]:
  assert (tim/(n+'.exitcode')).read_text()=='0'
  assert sha(tim/(n+'.tcl'))==sha(ROOT/'tools'/(n+'.tcl'))
 summary=(d/('mapfit'+suffix)/'output_files/board.fit.summary').read_text()
 fit=(d/('mapfit'+suffix)/'output_files/board.fit.rpt').read_text(errors='replace')
 le=int(re.search(r'Total logic elements\s*:\s*([\d,]+)',summary)[1].replace(',',''))
 ff=int(re.search(r'Total registers\s*:\s*(\d+)',summary)[1])
 lab=int(re.search(r'Total LABs:.*?;\s*(\d+) / 963',fit)[1]);m9k=int(re.search(r'M9Ks\s*; (\d+) / 56',fit)[1])
 timing={}
 for view in ['nominal','implementation']:
  r=rows(tim/(view+'-paths204.tsv'));assert len({x['corner'] for x in r})==3
  timing[view]={k:min([x for x in r if x['kind']==k and ((x['from_clock']=='nes')==(x['to_clock']=='nes'))],key=lambda x:float(x['slack'])) for k in ['setup','hold']}
 reset=rows(tim/'reset207.tsv');rtop=rows(tim/'reset207-topology.tsv')
 assert len(rtop)==2 and len({x['first'] for x in rtop})==2
 for x in rtop:assert x['fanout']==x['first'][:-3]+'[1]',x
 assert len(reset)==576 and len({x['to'] for x in reset})==96 and len({x['corner'] for x in reset})==3
 for x in reset:
  assert (':cold_release|' if index==1 else ':core_release|') in x['from'],x
  assert x['from'].endswith('|release_reset[1]'),x
  assert float(x['slack'])>=0,x
 inv=rows(tim/'inventory206.tsv');top=rows(tim/'topology206.tsv')
 assert len(top)==45 and len({x['first'] for x in top})==45
 for x in top:
  expected=x['first'].replace('epoch_meta','epoch_sync') if 'epoch_meta' in x['first'] else x['first'][:-3]+'[1]'
  assert x['fanout']==expected,x
 classifications=collections.Counter();classified=[];first={x['first'] for x in top};payload=[];gray=[]
 for x in inv:
  if ((x['from_clock']=='nes')==(x['to_clock']=='nes')):g='related_pll'
  elif x['kind'] in ['recovery','removal']:g='async_release_first_stages_or_inherited_review'
  elif x['to'] in first:
   g='gray_first_stage' if '|epoch_meta[' in x['to'] else 'control_first_stage'
   if g=='gray_first_stage' and x['kind']=='setup':gray.append(x)
  elif 'direct_path' in x['from'] and '|held[' in x['from'] and x['to']==x['from'].replace('|held[','|received['):
   g='held_payload_protocol'
   if x['kind']=='setup':payload.append(x)
  elif 'direct_path' in x['from'] or 'direct_path' in x['to']:g='new_other_review_open'
  else:g='inherited_unmodified'
  classifications[(x['corner'],x['kind'],g)]+=1;classified.append(dict(group=g,**x))
 assert not any(x['group']=='new_other_review_open' for x in classified)
 epoch_reset=[x for x in inv if x['kind'] in ['recovery','removal'] and 'content_lifetime' in x['to'] and re.search(r'\|(epoch_meta|epoch_sync|previous)\[',x['to'])]
 assert epoch_reset==[],epoch_reset[:3]
 heldmax=max(float(x['delay']) for x in payload);graymax=max(float(x['delay']) for x in gray)
 # Conservative one-receiver-cycle envelope minus2ns digital allowance.
 # Actual mailbox capture follows2FF plus a capture edge, held until ACK.
 # Gray does NOT rely on arbitrarily consecutive Gray transitions: load_begin
 # invalidates admission, and local release/stable comparison precedes use.
 heldmargin=round(11.904-heldmax-2,3);graymargin=round(45.454-graymax-2,3)
 assert heldmargin>0 and graymargin>0
 io_dir=d/('io'+suffix);assert (io_dir/'io.exitcode').read_text()=='0'
 assert sha(io_dir/'nes_boundary165_paths.tcl')==sha(ROOT/'tools/nes_boundary165_paths.tcl')
 io=measurements(io_dir);assert io==read(io_dir/'result.json')
 assert io['conditional_data_bounds_pass'] and io['native_payload_reset_pass']
 return dict(functional=test,fitted_le=le,registers=ff,lab=lab,m9k=m9k,le_spare=15408-le,lab_spare=963-lab,
  delta_from206=dict(le=le-15179,registers=ff-8360,lab=lab-959,m9k=m9k-47),timing=timing,
  related_timing_passed=all(float(timing[v][k]['slack'])>=0 for v in timing for k in timing[v]),
  reset=dict(registers=96,all_corner_paths=len(reset),min_recovery_ns=min(float(x['slack']) for x in reset if x['kind']=='recovery'),
   min_removal_ns=min(float(x['slack']) for x in reset if x['kind']=='removal'),crossclock_payload_paths=0,first_stage_single_fanouts=2),
  cdc=dict(rows=len(inv),first_stage_single_fanouts=45,held_payload_max_ns=heldmax,held_margin_after_2ns=heldmargin,
   gray_max_ns=graymax,gray_settle_margin_after_2ns=graymargin,new_other_data_paths=0,
   classifications=[dict(corner=c,kind=k,group=g,count=n) for (c,k,g),n in sorted(classifications.items())]),
  io=io),classified

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-board207';results={}
 for i in [1,2]:
  r,classified=candidate(d,i);results[str(i)]=r
  (a.out/f'classified0{i}.json').write_text(json.dumps(classified,indent=2)+'\n',encoding='utf8',newline='\n')
 previous=read(ROOT/'analysis/board206-verification.json')
 for n,h in previous['source_pins'].items():assert sha(ROOT/n)==h,n
 archives=[verify_archive(x['name']) for x in previous['prior_archives']]+[verify_archive('nes-board206')]
 base=read(BASE/'probes/nes-board206/source03/preparation206.json')['sources']
 selected=read(d/'source02/preparation207.json')['sources']
 changed=[n for n,h in base.items() if selected[n]!=h]
 assert set(changed)=={'board.qsf','nes_spi_boot.sv','nes_live_joint.sv'}
 assert set(selected)-set(base)=={'nes_source_epoch207.sv'}
 assert read(ROOT/'analysis/scroll193-measurement-plan.json')['collected_runs']==[]
 next_work=('Minimum actual board-C-SNES transfer/SEAL/display-ACK/retire pairing, then full paired ARM/ASM checks and FIRSTLEVELSCROLL; no unchanged codec/loader tests or seed loops.'
  if results['2']['related_timing_passed'] else
  'Shared-reset epoch boundary is functional and reset-timing clean, but related timing still fails. Inspect exact full-board critical path and joint resource budget; do not adopt, relax clocks, or repeat loader/seed micro-FIT loops. Minimum board-C-SNES pairing remains open.')
 r=dict(passed=True,meaning='Evidence consistency PASS; consult related_timing_passed separately, not deployment approval.',
  selected=['source02','epoch02','mapfit02','timing02','io02'],candidates=results,
  source_pins={n:sha(ROOT/n) for n in FILES},prior_archives=archives,unchanged_206_files=len(base)-len(changed),changed_206_files=changed,
  reused_206_direct_frames=9,reused_206_bytes=1968,reused_206_partial_checks=22,reused_206_cancel_checks=21,
  reused_206_loader=previous['loader'],reused_206_not_rerun=True,
  related_timing_passed=results['2']['related_timing_passed'],epoch_reset_passed=True,conditional_io_passed=True,
  new_exceptions=False,full_io_cdc_approved=False,mtbf_calculated=False,adopted=False,
  new_arm=False,new_asm=False,new_package=False,physical=False,actual_c_rtl_snes_cosim=False,actual_scroll_measured=False,meets_60fps_budget=False,next=next_work)
 text=json.dumps(r,indent=2)+'\n';(a.out/'result.json').write_text(text,encoding='utf8',newline='\n');(ROOT/'analysis/board207-verification.json').write_text(text,encoding='utf8',newline='\n')
 print(json.dumps(dict(passed=True,related_timing_passed=r['related_timing_passed'],epoch_reset_passed=True,prior_archives=len(archives))))
if __name__=='__main__':main()
