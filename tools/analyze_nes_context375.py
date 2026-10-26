# SPDX-License-Identifier: MIT
"""Reconcile host context375 against373: actual schedules, port safety and whole cost."""
import argparse,collections,json,re
from pathlib import Path
import analyze_nes_source368 as old
from analyze_nes_receipt335 import load_image
from analyze_nes_dual373 import self_costs
from nes_context375 import COMMON,CHANGED,DIRECTORY
from nes_bg295 import unbatch
from nes_delta231 import ROOT,BASE,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--map',type=Path,required=True);p.add_argument('--guards',type=Path,required=True);p.add_argument('--negatives',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 d=a.run.resolve();board=a.map.resolve();ref=BASE/'probes/nes-dual373/joint03';bm=BASE/'probes/nes-dual373/map03'
 current=old.measure(d,916,0);before=old.measure(ref,916,0);ev=old.events(d);pairs=[]
 assert load_image(d/'output.elf')==load_image(ref/'output.elf')
 for x,y in zip(current['rows'],before['rows']):
  f=x['frame'];assert f==y['frame'];same=(x['start_ps'],x['start_ROM_cycle'])==(y['start_ps'],y['start_ROM_cycle'])
  if 907<=f<=916:assert same,(f,'fixed source origin')
  ta=old.js(d/f'arm{f}.json')['transfers'];tb=old.js(ref/f'arm{f}.json')['transfers']
  payload=lambda t:[i['rx'] for i in t if i.get('source_phase367')==2 and i['rx']]
  hints=lambda t:[i['tx'] for i in t if i['tx'].startswith('ea') and len(i['tx'])==56]
  assert payload(ta)==payload(tb) and hints(ta)==hints(tb)
  pa=d/f'actual-plans293-{f}.bin';pb=ref/f'actual-plans293-{f}.bin';old.PINS[str(pa)]=sha(pa);old.PINS[str(pb)]=sha(pb)
  assert pa.read_bytes()==pb.read_bytes() and unbatch(pa.read_bytes())==unbatch(pb.read_bytes())
  pairs.append(dict(frame=f,before_ms=y['processing_ms'],after_ms=x['processing_ms'],delta_ms=x['processing_ms']-y['processing_ms'],same_source_start_ROM_cycle=same,
   before_start_ps=y['start_ps'],after_start_ps=x['start_ps'],before_materialized_ms=y['materialized_ms'],after_materialized_ms=x['materialized_ms'],before_BG=y.get('BG'),after_BG=x.get('BG'),before_OBJ=y.get('OBJ'),after_OBJ=x.get('OBJ'),before_SPI=y['total_SPI_bytes'],after_SPI=x['total_SPI_bytes']))
 for x,y in zip(current['captures'],before['captures']):assert x['frame']==y['frame'] and x['at_ps']==y['at_ps'] and x['admitted'] and y['admitted']
 assert old.js(d/'manifest368.json')['fixed_capture907']==5371247
 after=old.whole(board);prior=old.whole(bm);costs=[self_costs(x) for x in (bm,board)]
 assert sum(v['comb'] for v in costs[0].values())==prior['comb'] and sum(v['comb'] for v in costs[1].values())==after['comb']
 compiled=set(re.findall(r'-name SYSTEMVERILOG_FILE\s+"?([^\s"]+)',old.read(board/'board.qsf')));mods={};shared={}
 for n in compiled:
  if (board/n).exists():
   for mod in re.findall(r'^\s*module\s+(\w+)',(board/n).read_text(errors='replace'),re.M):mods[mod]=board/n
 for n in set(old.js(d/'manifest367.json')['sources'])|set(COMMON):
  for mod in re.findall(r'^\s*module\s+(\w+)',old.read(d/n),re.M):
   if mod in mods:assert sha(d/n)==sha(mods[mod]);shared[mod]=sha(d/n)
 assert len(shared)==31
 for n in CHANGED:assert sha(DIRECTORY/n)==sha(d/n)==sha(board/n)
 manifest=old.js(DIRECTORY/'manifest.json')
 for n,h in manifest['source_files'].items():assert sha(DIRECTORY/n)==h
 for n in COMMON:assert sha(d/n)==sha(board/n)
 guards=old.js(a.guards/'result.json');assert guards['passed'] and guards['cases']==8
 assert guards['source']['nes_host_context375.sv']==sha(d/'nes_host_context375.sv')
 for case in range(8):
  raw=old.read(a.guards/f'case{case}.log');assert f'PASS CONTEXT375 case={case}' in raw and 'Errors: 0, Warnings: 0' in raw
 negatives=old.js(a.negatives);assert negatives['passed'] and [x['case'] for x in negatives['cases']]==list(range(4))
 for x in negatives['cases']:
  assert x['passed']
  for n,h in x['RTL'].items():assert sha(d/n)==h
 retained=old.js(BASE/'probes/nes-dual373/guards03/result.json')
 for n,h in retained['source_hashes'].items():
  if (d/n).exists():assert sha(d/n)==h
 stores=[x for x in ev if x[0]=='context_store375'];checks=[x for x in ev if x[0]=='context_check375']
 used=sorted({int(x[2]) for x in stores});assert used==list(range(13)) and checks
 # The actual trace guards assert port-B exclusion from716..767,immutable CDC/head,
 # MAP allocation freeze and no cold comparison during actual DMA reads.
 bench=old.read(d/'joint266_tb.sv')
 for marker in ('validator read/write entered reserved52B375','shared context lost immutable queue head375','cold RAM token fetch during actual read375','DMA before cold token verify375','CDC context changed during active display375'):
  assert marker in bench
 flow=old.read(d/'nes_mux260.sv');core=old.read(d/'nes_joint257.sv');helper=old.read(d/'nes_host_context375.sv')
 assert 'active305.token' not in flow and 'reg [83:0] admitted286' not in flow and '.load_enable312(1\'b0)' in flow
 assert 'wire [83:0] admitted286=full_idata278' in flow and 'ctx_check_busy375&&owner==MAP&&allocate' in flow
 assert 'memory[ctx_absolute375]<=ctx_data375' in core and 'ctx_write375&&init278&&!reset&&!abort_source&&!fault&&ctx_address375<52' in core
 assert 'wire [7:0] at=cursor375' in helper and 'reg [7:0] at' not in helper
 assert 'check_lane375=at[1:0]-2\'d1' in helper
 report=(board/'output_files/board.map.rpt').read_bytes().decode('ascii',errors='replace')
 ram=[x for x in report.splitlines() if '|nes_joint257:core|altsyncram:memory_rtl_0|' in x and 'True Dual Port' in x]
 assert len(ram)==1 and re.search(r'True Dual Port\s*;\s*1024\s*;\s*8\s*;\s*1024\s*;\s*8\s*;\s*8192',ram[0])
 reads=[int(x[-1]) for x in ev if x[0]=='read336'];starts={};overlap=collections.Counter();gaps=[];prev=None
 for x in ev:
  if x[0]=='read336':
   key=(x[1],x[2]);t=int(x[-1])
   if prev and prev[0]==key:gaps.append(t-prev[1])
   prev=(key,t)
  if x[0]=='ARM_wire_start334':starts[(x[1],x[2])]=int(x[4])
  if x[0]=='arm267' and (x[1],x[2]) in starts:
   n=sum(starts[(x[1],x[2])]<=t<=int(x[4]) for t in reads)
   if n:overlap[int(x[2])]+=n
 completions=[dict(frame=x['frame'],interval_ms=(int(old.event(ev,'frame_done',x['frame'])[2])-int(old.event(ev,'frame_done',x['frame']-1)[2]))/1e9) for x in current['rows'][2:]]
 names=['nes_core257:encoder','nes_transport257:transport','nes_spi270:spi_front270','nes_validator278:validator','nes_output260:flow','nes_plan_batch206:transport','nes_plan_spi200:endpoint','nes_queue260:queue']
 pools=[{n:next(v['comb'] for k,v in c.items() if k.endswith('|'+n)) for n in names} for c in costs]
 # The new helper is a child with disjoint self area;charge it explicitly.
 helper_cost={k:v for k,v in costs[1].items() if 'nes_host_context375:' in k};assert helper_cost
 extra=sum(v['comb'] for v in helper_cost.values());pool=sum(pools[1].values())+extra;retained_comb=pools[1][names[0]]+pools[1][names[3]]
 delta_rows=sorted([dict(path=k,before=costs[0].get(k,{}).get('comb',0),after=costs[1].get(k,{}).get('comb',0),delta=costs[1].get(k,{}).get('comb',0)-costs[0].get(k,{}).get('comb',0)) for k in set(costs[0])|set(costs[1])],key=lambda x:abs(x['delta']),reverse=True)
 for f in (ROOT/'tools').glob('*375*'):old.PINS[str(f)]=sha(f)
 result=dict(stage=375,analysis_passed=True,continuous_capture_passed=True,candidate=current,baseline373=before,paired=pairs,
  unchanged_ARM_PT_LOAD=True,source_hint_wire_plan_exact373=True,shared_compiled_modules=shared,guards=guards,actual_negatives=negatives,retained_source_context_guards=retained,
  context=dict(aperture=[716,767],bytes=52,actual_written_offsets=used,actual_header_bytes=len(used),writes=len(stores),cold_token_checks=len(checks),
   existing_shared_cursor=True,removed_duplicate_identity_bits=84,removed_active_token_bits=32,active_record_logical_bits_before=121,active_record_logical_bits_after=89,
   token_per_DMA_byte_fetches=0,existing_immutable_aperture_token_cache=True,postinit_validator_port_B_excluded=True,actual_trace_guarded=True,
   minimum_observed_read_period_ps=min(gaps),read_bytes_during_command_windows=dict(overlap),WCET=False),
  whole_MAP=dict(before=prior,after=after,delta={k:after[k]-prior[k] for k in after},disjoint_self_before=pools[0],disjoint_self_after=pools[1],new_helper_self=helper_cost,self_deltas=delta_rows),
  replacement_budget=dict(eight_module_pool_with_helper=pool,retained_codec_checker=retained_comb,control_with_helper=pool-retained_comb,required_with155reserve=after['comb']-15253,
   all_eight_and_helper_ceiling=pool-(after['comb']-15253),retained_codec_control_ceiling=pool-retained_comb-(after['comb']-15253)),
  comb_deficit=after['comb']-15408,required_with155reserve=after['comb']-15253,completion_intervals=completions,
  ARM_size=old.js(ROOT/'analysis/frontier372-verification.json')['ARM_size']['after'],ARM_stack_observed=current['stack_observed'],
  selected_experimental_RTL=375,full_host_executor_replaced=False,selected_for_board=False,FIT=False,STA=False,physical=False,sustained60fps=False,
  limits=['Compiled372 M4 at CPI1/84MHz with explicit IRQ/peripheral allocations,not hardware WCET.','Ready-gated ROM stress;ordinary65816 trace and map DMA/display models,not fullCPU/VBlank/liveNES.','12frames905..916,next917 capture;not71/heavy7/multiple phases/session/physical validation.','Only13B header context is stored;not all42B context or full descriptor/manifest/receipt/SPI/plan interpreter.','Port-B exclusion and no DMA cold lookup are trace guards plus bounded RTL address audit,not unconstrained all-state proof.','Four actual injected negatives freeze RAM and block completion;worker intentionally cancelled,not successful post-STOP normal recovery.','Whole comb still exceeds capacity;no FIT/STA or physical60fps approval.'],pins=old.PINS)
 a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',newline='\n')
 print(json.dumps({k:result[k] for k in ('paired','context','whole_MAP','replacement_budget','comb_deficit','completion_intervals')},indent=2))
if __name__=='__main__':main()
