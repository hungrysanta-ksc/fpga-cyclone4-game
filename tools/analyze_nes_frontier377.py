# SPDX-License-Identifier: MIT
"""Actual377 M4 frontier schedule on byte-identical375 RTL;no fresh area claim."""
import argparse,json
from pathlib import Path
import analyze_nes_source368 as old
from analyze_nes_receipt335 import load_image
from nes_context375 import COMMON,CHANGED,DIRECTORY
from nes_bg295 import unbatch
from nes_delta231 import ROOT,BASE,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--causal',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 d=a.run.resolve();ref=BASE/'probes/nes-context375/joint01';board=BASE/'probes/nes-context375/map03';current=old.measure(d,916,0);before=old.measure(ref,916,0);ev=old.events(d);pairs=[]
 # Reusing a wholeMAP is justified by every shared RTL input,not an unchanged top wrapper.
 for n in COMMON:assert sha(d/n)==sha(ref/n)==sha(board/n);old.read(d/n)
 inherited={}
 for n in set(old.js(ref/'manifest367.json')['sources'])|set(COMMON):
  if (board/n).exists():assert sha(d/n)==sha(ref/n)==sha(board/n);inherited[n]=sha(d/n)
 for n in CHANGED:assert sha(DIRECTORY/n)==sha(d/n)
 assert load_image(d/'output.elf')==load_image(d/'../profile02/output.elf')
 for x,y in zip(current['rows'],before['rows']):
  f=x['frame'];assert f==y['frame'];same=(x['start_ps'],x['start_ROM_cycle'])==(y['start_ps'],y['start_ROM_cycle'])
  if 907<=f<=916:assert same,(f,'fixed source origin')
  txs=[old.js(v/f'arm{f}.json')['transfers'] for v in (d,ref)]
  payload=lambda t:[i['rx'] for i in t if i.get('source_phase367')==2 and i['rx']]
  assert payload(txs[0])==payload(txs[1])
  pa=d/f'actual-plans293-{f}.bin';pb=ref/pa.name;old.PINS[str(pa)]=sha(pa);old.PINS[str(pb)]=sha(pb)
  assert pa.read_bytes()==pb.read_bytes() and unbatch(pa.read_bytes())==unbatch(pb.read_bytes())
  pairs.append(dict(frame=f,before_ms=y['processing_ms'],after_ms=x['processing_ms'],delta_ms=x['processing_ms']-y['processing_ms'],same_source_start_ROM_cycle=same,
   before_materialized_ms=y['materialized_ms'],after_materialized_ms=x['materialized_ms'],before_BG=y.get('BG'),after_BG=x.get('BG'),before_OBJ=y.get('OBJ'),after_OBJ=x.get('OBJ'),
   before_SPI=y['total_SPI_bytes'],after_SPI=x['total_SPI_bytes'],before_hints=y['hints'],after_hints=x['hints'],before_ARM_instructions=y['ARM_instructions'],after_ARM_instructions=x['ARM_instructions']))
 for x,y in zip(current['captures'],before['captures']):assert x['frame']==y['frame'] and x['at_ps']==y['at_ps'] and x['admitted'] and y['admitted']
 assert old.js(d/'manifest368.json')['fixed_capture907']==5371247
 proof=old.js(a.causal);assert proof['passed'] and len(proof['negative_guards'])==9 and proof['object_ABI_exact']
 assert proof['pins'][str(d/'output.elf')]==sha(d/'output.elf')
 costs=dict(before=old.size(ref/'output.elf'),after=old.size(d/'output.elf'));costs['delta']={k:costs['after'][k]-costs['before'][k] for k in costs['before']};assert costs['delta']['data']==costs['delta']['BSS']==0
 completions=[dict(frame=x['frame'],interval_ms=(int(old.event(ev,'frame_done',x['frame'])[2])-int(old.event(ev,'frame_done',x['frame']-1)[2]))/1e9) for x in current['rows'][2:]]
 previous=old.js(ROOT/'analysis/context375-verification.json');area=old.whole(board)
 retained=previous['actual_negatives']
 for c in retained['cases']:
  for n,h in c['RTL'].items():assert sha(d/n)==h
 for f in ROOT.joinpath('tools').glob('*377*'):old.PINS[str(f)]=sha(f)
 warm=current['rows'][2:];budget=1000/60
 r914=next(x for x in warm if x['frame']==914);fill=old.event(ev,'hint_fill367',914)
 fill_ms=(int(fill[2])-r914['start_ps'])/1e9;close_ms=(354640-r914['start_ROM_cycle']%357368)*45454/1e9
 result=dict(stage=377,analysis_passed=True,candidate=current,baseline375=before,paired=pairs,causal=proof,unchanged_RTL=True,
  shared_RTL={n:sha(d/n) for n in COMMON},all_common_sim_board_files=inherited,source_payload_wire_plan_exact375=True,ARM_size=costs,ARM_stack_observed=current['stack_observed'],
  completion_intervals=completions,max_warm_processing_ms=max(x['processing_ms'] for x in warm),max_warm_completion_interval_ms=max(x['interval_ms'] for x in completions if x['frame']>907),
  processing_over_60Hz=[dict(frame=x['frame'],excess_ms=x['processing_ms']-budget) for x in warm if x['processing_ms']>budget],
  unreserved_model_processing_slack_ms=budget-max(x['processing_ms'] for x in warm),mapper_safe_allowance_ms=None,mapper_extra_time_measured=False,
  first914_hint_fill_ms=fill_ms,first914_ROM_window_close_approx_ms=close_ms,first914_ROM_window_slack_approx_ms=close_ms-fill_ms,
  reserve_scenarios=[dict(reserve_ms=v,additional_reduction_needed_ms=max(0,max(x['processing_ms'] for x in warm)+v-budget),measured_mapper_cost=False) for v in (.25,.5,1,2)],
  whole_MAP=dict(inherited_stage=375,selected_MAP='map03',after=area,delta={'LE':0,'comb':0,'FF':0,'RAM_bits':0},new_MAP=False),
  comb_deficit=area['comb']-15408,required_with155reserve=area['comb']-15253,retained_independent_guards=retained,
  selected_RTL=375,MMC4_MMC5_implemented=False,FIT=False,STA=False,physical=False,sustained60fps=False,
  limits=['M4 CPI1/84MHz with explicitIRQ/peripheral allocations;not hardwareWCET.','12frames905..916 and next917capture;not71/heavy7/multiple ROM phases or live mapper workload.','375 ROM bench fixes core_safe=1 with synthetic core demand;actual mapper/core bus eligibility must be measured.','Ordinary65816 trace andmapDMA/display busmodels,not fullCPU/VBlank/physical frame pacing.','ROM address/tag/cell/exception/loader limits of mapper376 audit remain;no MMC4/MMC5 area/time allowance has been proven.','Source/hint changes have no DMA authority;actual plans and independent expected/read checks remain binding.'],pins=old.PINS)
 a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',newline='\n');print(json.dumps({k:result[k] for k in ('paired','ARM_size','max_warm_processing_ms','max_warm_completion_interval_ms','processing_over_60Hz','unreserved_model_processing_slack_ms')},indent=2))
if __name__=='__main__':main()
