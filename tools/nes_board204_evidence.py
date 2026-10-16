# SPDX-License-Identifier: MIT
"""Join board204 evidence without treating FIT success as timing approval."""
from pathlib import Path
import argparse,json,csv,re
from nes_metadata203 import ROOT,BASE,sha
from nes_bulk194_evidence import verify_archive

FILES=['src/nes/rtl/nes_source_epoch204.sv','src/nes/rtl/nes_direct204.sv',
 'tools/nes_board204.py','tools/test_nes_board204.py','tools/test_nes_epoch204.py',
 'tests/nes-functional/source_epoch204_tb.sv','tools/nes_board204_report.py',
 'tools/nes_board204_timing.tcl','tools/nes_board204_paths.tcl','tools/nes_board204_evidence.py',
 'docs/nes-board204-contract.ko.md']
def read(p):return json.loads(p.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-board204';prep=read(d/'source01/preparation204.json')
 for name in ['source01','map01','fit01','timing01','paths01']:
  for n,h in prep['sources'].items():
   if n=='board.qsf' and name in ['timing01','paths01']:
    # STA changes line endings and LAST_QUARTUS_VERSION metadata only.
    original=(d/'source01'/n).read_text()
    expected=original.replace('LAST_QUARTUS_VERSION "25.1std.0 Lite Edition"','LAST_QUARTUS_VERSION "25.1std.0 Standard Edition"')
    assert (d/name/n).read_text()==expected,(name,n)
   else:assert sha(d/name/n)==h,(name,n)
 for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
 for name,tool in [('test01','test_nes_board204.py'),('epoch01','test_nes_epoch204.py')]:
  r=read(d/name/'result.json');assert r['passed'] and r['script_sha256']==sha(ROOT/'tools'/tool)
  for n,h in r['source_pins'].items():assert sha(BASE/n)==h,n
 test=read(d/'test01/result.json');epoch=read(d/'epoch01/result.json')
 assert sum(x['bytes'] for x in test['cases'])==1968 and sum(x['frames'] for x in test['cases'])==9 and epoch['checks']==20
 assert 'nes_native_fill165' not in (d/'source01/nes_live_joint.sv').read_text()
 assert sha(d/'source01/board.sdc')==prep['baseline']['board.sdc'] and sha(d/'source01/cdc181.sdc')==prep['baseline']['cdc181.sdc']
 assert (d/'map01/map.exitcode').read_text()=='0' and (d/'fit01/fit.exitcode').read_text()=='0'
 fit=(d/'fit01/output_files/board.fit.rpt').read_bytes().decode('cp949',errors='replace')
 assert re.search(r'Total LABs:.*?963 / 963',fit) and re.search(r'M9Ks\s*; 47 / 56',fit)
 assert '15,310 / 15,408' in (d/'fit01/output_files/board.fit.summary').read_text()
 timing={}
 for view in ['nominal','implementation']:
  rows=list(csv.DictReader((d/'timing01'/(view+'-paths204.tsv')).open(),delimiter='\t'))
  assert len(set(x['corner'] for x in rows))==3
  timing[view]={}
  for related in [True,False]:
   for kind in ['setup','hold']:
    hits=[x for x in rows if x['kind']==kind and ((x['from_clock']=='nes')==(x['to_clock']=='nes'))==related]
    timing[view][('related_' if related else 'unreviewed_nes_cross_')+kind]=min(hits,key=lambda x:float(x['slack']))
 assert float(timing['nominal']['related_setup']['slack'])==-0.638
 assert float(timing['nominal']['related_hold']['slack'])==0.150
 for name,script in [('timing01','nes_board204_timing.tcl'),('paths01','nes_board204_paths.tcl')]:
  assert sha(d/name/script)==sha(ROOT/'tools'/script)
 report=read(d/'report01/result.json');assert report['script_sha256']==sha(ROOT/'tools/nes_board204_report.py')
 for key in ['baseline','candidate']:assert sha(BASE/report[key]['path'])==report[key]['sha256']
 previous=read(ROOT/'analysis/metadata203-verification.json')
 for n,h in previous['source_pins'].items():assert sha(ROOT/n)==h,n
 archives=[verify_archive(x['name']) for x in previous['prior_archives']]+[verify_archive('nes-metadata203')]
 assert read(ROOT/'analysis/scroll193-measurement-plan.json')['collected_runs']==[]
 result=dict(passed=True,meaning='Evidence consistency PASS; candidate is NOT timing-approved or deployable.',
  selected=['source01','test01','epoch01','map01','fit01','timing01','paths01','report01'],
  source_pins={n:sha(ROOT/n) for n in FILES},prior_archives=archives,
  result_pins={n:sha(d/n/'result.json') for n in ['test01','epoch01','report01']},
  functional_frames=9,bytes=1968,epoch_checks=20,board_binding=True,old_fill_removed=True,
  fit_passed=True,fitted_le=15310,lab=963,m9k=47,le_spare=98,lab_spare=0,timing=timing,
  nominal_setup_passed=False,full_io_cdc_approved=False,adopted=False,actual_c_rtl_snes_cosim=False,
  new_full_arm=False,reused_arm203_margin=9260,new_package=False,physical=False,actual_scroll_measured=False,meets_60fps_budget=False,
  next='Remove raw loader status bypass into NES data enables; explicit invalidation/admission and exact new CDC bounds. Budget tile191 register buffer vs bulk193 sealed RAM and descriptor copies, then related-check routing and minimum joint proof before one justified FIT. Do not restart loader microFIT/seed loops. Full IO/C+SNES pair then actual FIRSTLEVELSCROLL.')
 text=json.dumps(result,indent=2)+'\n';(a.out/'result.json').write_text(text,encoding='utf8');(ROOT/'analysis/board204-verification.json').write_text(text,encoding='utf8')
 print(json.dumps(dict(passed=True,fit=True,timing_approved=False,le=15310,lab=963,m9k=47,prior_archives=len(archives))))
if __name__=='__main__':main()
