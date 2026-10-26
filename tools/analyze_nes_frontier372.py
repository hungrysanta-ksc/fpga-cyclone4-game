# SPDX-License-Identifier: MIT
"""Actual source schedule,independent consumption and whole retained RTL cost."""
import argparse,json,re
from pathlib import Path
import analyze_nes_source368 as old
from analyze_nes_receipt335 import load_image
from analyze_nes_ingress371 import symbols
from nes_capture368 import COMMON
from nes_delta231 import ROOT,BASE,sha
from nes_bg295 import unbatch

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.run.resolve();root=BASE/'probes/nes-frontier372'
 read=old.read;js=old.js;log=read(d/'vsim.log');miss=int('Fatal: capture coverage367' in log)
 current=old.measure(d,915,miss);before=old.measure(BASE/'probes/nes-source370/joint02',914,1);pairs=[]
 for x,y in zip(current['rows'][2:],before['rows'][2:]):
  assert x['frame']==y['frame'];same=(x['start_ps'],x['start_ROM_cycle'])==(y['start_ps'],y['start_ROM_cycle'])
  if x['frame']<=909:assert same
  pairs.append(dict(frame=x['frame'],before_ms=y['processing_ms'],after_ms=x['processing_ms'],delta_ms=x['processing_ms']-y['processing_ms'],same_start_ROM_phase=same,
   before_materialized_ms=y['materialized_ms'],after_materialized_ms=x['materialized_ms'],source_SPI_before=y['source_SPI_bytes']+8,source_SPI_after=x['source_SPI_bytes']+8,total_SPI_before=y['total_SPI_bytes'],total_SPI_after=x['total_SPI_bytes']))
  prior=BASE/f"probes/nes-source370/joint02/arm{x['frame']}.json";actual=js(d/f"arm{x['frame']}.json")['transfers'];prior=js(prior)['transfers']
  payload=lambda ts:[t['rx'] for t in ts if t.get('source_phase367')==2 and t['rx']]
  hints=lambda ts:[t['tx'] for t in ts if len(t['tx'])==56 and t['tx'].startswith('ea')]
  assert payload(actual)==payload(prior) and hints(actual)==hints(prior)
  for folder in (d,BASE/'probes/nes-source370/joint02'):
   f=folder/f"actual-plans293-{x['frame']}.bin";old.PINS[str(f)]=sha(f)
  assert unbatch((d/f"actual-plans293-{x['frame']}.bin").read_bytes())==unbatch((BASE/f"probes/nes-source370/joint02/actual-plans293-{x['frame']}.bin").read_bytes())
 board=BASE/'probes/nes-source368/map01';m=js(board/'result.json');compiled=set(re.findall(r'-name SYSTEMVERILOG_FILE\s+"?([^\s"]+)',read(board/'board.qsf')));modules={};shared={}
 for n in COMMON:read(d/n);assert sha(d/n)==sha(board/n)==m['shared_boundary'][n]
 for n in compiled:
  if (board/n).exists():
   for mod in re.findall(r'^\s*module\s+(\w+)',read(board/n),re.M):modules[mod]=board/n
 for n in js(d/'manifest367.json')['sources']:
  for mod in re.findall(r'^\s*module\s+(\w+)',read(d/n),re.M):
   if mod in modules:assert sha(d/n)==sha(modules[mod]);shared[mod]=sha(d/n)
 assert len(shared)==30
 ref=root/'build06/output.elf';old.PINS[str(ref)]=sha(ref)
 assert load_image(d/'output.elf')==load_image(ref) and symbols(d/'output.elf')==symbols(ref)
 assert load_image(d/'pre372-output.elf')==load_image(BASE/'probes/nes-source370/joint02/output.elf')
 for n in ('nes_frontier372.py','probe_nes_frontier372.py'):read(d/n);read(ROOT/'tools'/n);assert sha(d/n)==sha(ROOT/'tools'/n)
 check=js(root/'check05.json');guards=js(root/'guards04/result.json');control=js(root/'control05.json')
 assert all(x['passed'] for x in (check,guards,control)) and sha(ref) in check['pins'].values() and guards['ELF']==sha(ref)
 assert check['direct_cases']==2573 and check['objects']==96
 costs=dict(before=old.size(d/'pre372-output.elf'),after=old.size(d/'output.elf'));costs['delta']={k:costs['after'][k]-costs['before'][k] for k in costs['before']}
 report=old.whole(board);newer=old.whole(BASE/'probes/nes-source371/map01');delta={k:report[k]-newer[k] for k in report}
 warm=current['rows'][2:];worst=max(warm,key=lambda x:x['processing_ms']);c915=next(x for x in current['captures'] if x['frame']==915);c916=next(x for x in current['captures'] if x['frame']==916)
 assert c915['admitted'] and not c916['admitted'] and current['rows'][-1]['frame']==915
 wide=read(root/'joint01/vsim.log');assert 'Fatal: next capture deadline missed367 frame915' in wide
 row=current['rows'][-1];late_start=(row['start_ps']-c916['at_ps'])/1e9
 for p in ROOT.joinpath('tools').glob('*372.py'):read(p)
 result=dict(stage=372,analysis_passed=True,continuous_capture_passed=False,source_payload_and_hint_exact370=True,semantic_plan_records_exact370=True,
  candidate=current,baseline370=before,paired=pairs,check=check,retained_guards=guards,control_audit=control,
  ARM_size=costs,guarded_ELF_images_and_symbols_equal=True,all_shared_modules=shared,
  whole_MAP=dict(values=report,inherited_from368_370=True,new_MAP=False,delta_vs370=dict(LE=0,comb=0,FF=0,RAM_bits=0),delta_vs371=delta),
  comb_deficit=report['comb']-15408,deletion_needed_with155reserve=report['comb']-15253,actual_control_replacement_implemented=False,new_control_area_saving=0,
  capture915_admitted=True,first_missed_capture=916,source915_starts_after916_deadline_ms=late_start,
  worst_warm_frame=worst['frame'],worst_warm_ms=worst['processing_ms'],warm_budget_margin_ms=1000/60-worst['processing_ms'],
  nonselected_wide=dict(first_missed_capture=915,full914_timing_measured=False),FIT=False,STA=False,physical=False,sustained60fps=False,
  scope='Actual compiled M4/source/SPI/IRQ/2slot and ROM origin accounting;CPI1/84MHz/peripheral/exception adapters;ordinary65816 trace and DMA/finaldisplay busmodels. Unchanged VBlank firmware,not fullCPU/VBlank/WCET/71/heavy7/multiple phases/physical.',pins=old.PINS)
 a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',newline='\n')
 print(json.dumps(dict(pairs=pairs,capture915=c915,capture916=c916,late_source915_ms=late_start,worst=worst,ARM=costs),indent=2))
if __name__=='__main__':main()
