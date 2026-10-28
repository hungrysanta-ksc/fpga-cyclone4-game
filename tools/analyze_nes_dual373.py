# SPDX-License-Identifier: MIT
"""Reconcile dual373 schedules, independent reads, ROM origins and whole Lite cost."""
import argparse,json,re
from pathlib import Path
import analyze_nes_source368 as old
from analyze_nes_receipt335 import load_image
from nes_dual373 import COMMON,CHANGED,DIRECTORY
from nes_delta231 import ROOT,BASE,sha
from nes_bg295 import unbatch

def self_costs(d):
 result={}
 path=d/'output_files/board.map.rpt';old.PINS[str(path)]=sha(path)
 for line in path.read_bytes().decode('ascii',errors='replace').splitlines():
  cells=[x.strip() for x in line.split(';')]
  if len(cells)>13 and re.match(r'\d+ \(',cells[2]):
   result[cells[-4]]=dict(comb=int(re.search(r'\((\d+)\)',cells[2])[1]),FF=int(re.search(r'\((\d+)\)',cells[3])[1]))
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--map',type=Path,required=True);p.add_argument('--guards',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.run.resolve();board=a.map.resolve()
 current=old.measure(d,916,0);baseline=old.measure(BASE/'probes/nes-frontier372/joint02',915,1)
 ref=BASE/'probes/nes-frontier372/joint02';pairs=[]
 assert load_image(d/'output.elf')==load_image(ref/'output.elf')
 for x,y in zip(current['rows'],baseline['rows']):
  f=x['frame'];assert f==y['frame']
  ta=old.js(d/f'arm{f}.json')['transfers'];tb=old.js(ref/f'arm{f}.json')['transfers']
  payload=lambda t:[x['rx'] for x in t if x.get('source_phase367')==2 and x['rx']]
  hints=lambda t:[x['tx'] for x in t if len(x['tx'])==56 and x['tx'].startswith('ea')]
  assert payload(ta)==payload(tb),(f,'source payload')
  assert hints(ta)==hints(tb),(f,'causal hint')
  assert unbatch((d/f'actual-plans293-{f}.bin').read_bytes())==unbatch((ref/f'actual-plans293-{f}.bin').read_bytes()),(f,'semantic plan')
  for folder in (d,ref):old.PINS[str(folder/f'actual-plans293-{f}.bin')]=sha(folder/f'actual-plans293-{f}.bin')
  pairs.append(dict(frame=f,before_ms=y['processing_ms'],after_ms=x['processing_ms'],delta_ms=x['processing_ms']-y['processing_ms'],
   same_source_start_and_ROM_cycle=(x['start_ps'],x['start_ROM_cycle'])==(y['start_ps'],y['start_ROM_cycle']),
   before_start_ps=y['start_ps'],after_start_ps=x['start_ps'],before_materialized_ms=y['materialized_ms'],after_materialized_ms=x['materialized_ms'],
   before_source_SPI_bytes=y['source_SPI_bytes']+8,after_source_SPI_bytes=x['source_SPI_bytes']+8,
   before_total_SPI_bytes=y['total_SPI_bytes'],after_total_SPI_bytes=x['total_SPI_bytes']))
 assert old.js(d/'manifest368.json')['fixed_capture907']==5371247
 assert old.js(ref/'manifest368.json')['fixed_capture907']==5371247
 assert next(x for x in pairs if x['frame']==907)['same_source_start_and_ROM_cycle']
 ev=old.events(d)
 captures={x['frame']:x for x in current['captures']};bc={x['frame']:x for x in baseline['captures']}
 for f in set(captures)&set(bc):assert captures[f]['at_ps']==bc[f]['at_ps'],('fixed capture origin',f)
 # Frame907 is fixed before the independent capture loop; ROM counter is never reset at source start.
 starts=current['rows'];completion=[];overlap=[]
 for i,x in enumerate(starts[2:],2):
  end=int(old.event(ev,'frame_done',x['frame'])[2]);prev=int(old.event(ev,'frame_done',x['frame']-1)[2]);
  completion.append(dict(frame=x['frame'],completion_interval_ms=(end-prev)/1e9))
  if x['start_ps']<prev:overlap.append(dict(frame=x['frame'],source_start_before_previous_display_done_ms=(prev-x['start_ps'])/1e9,
   materialized_before_previous_display_done_ms=(prev-(x['start_ps']+x['materialized_ms']*1e9))/1e9,
   source_start_before_previous_actual_retire_ms=(int(old.event(ev,'retired368',x['frame']-905)[2])-x['start_ps'])/1e9,
   materialized_before_previous_actual_retire_ms=(int(old.event(ev,'retired368',x['frame']-905)[2])-(x['start_ps']+x['materialized_ms']*1e9))/1e9))
 before=old.whole(BASE/'probes/nes-source368/map01');after=old.whole(board)
 names=['nes_core257:encoder','nes_transport257:transport','nes_spi270:spi_front270','nes_validator278:validator','nes_output260:flow','nes_plan_batch206:transport','nes_plan_spi200:endpoint','nes_queue260:queue']
 costs=[self_costs(x) for x in (BASE/'probes/nes-source368/map01',board)];pool=[]
 for cost in costs:
  assert sum(x['comb'] for x in cost.values()) in (before['comb'],after['comb'])
  pool.append({n:next(v['comb'] for k,v in cost.items() if k.endswith('|'+n)) for n in names})
 delta_rows=sorted([dict(path=k,before=costs[0].get(k,{}).get('comb',0),after=costs[1].get(k,{}).get('comb',0),
  delta=costs[1].get(k,{}).get('comb',0)-costs[0].get(k,{}).get('comb',0)) for k in set(costs[0])|set(costs[1])],key=lambda x:abs(x['delta']),reverse=True)
 compiled=set(re.findall(r'-name SYSTEMVERILOG_FILE\s+"?([^\s"]+)',old.read(board/'board.qsf')));modules={};shared={}
 for n in compiled:
  if (board/n).exists():
   for mod in re.findall(r'^\s*module\s+(\w+)',(board/n).read_text(errors='replace'),re.M):modules[mod]=board/n
 src=old.js(d/'manifest367.json')['sources']
 for n in set(src)|set(COMMON):
  for mod in re.findall(r'^\s*module\s+(\w+)',old.read(d/n),re.M):
   if mod in modules:assert sha(d/n)==sha(modules[mod]),mod;shared[mod]=sha(d/n)
 assert len(shared)==30
 manifest=old.js(DIRECTORY/'manifest.json')
 for n,h in manifest['source_files'].items():assert sha(DIRECTORY/n)==h==sha(board/n);old.read(DIRECTORY/n)
 for n in COMMON:assert sha(d/n)==sha(board/n)
 guard=old.js(a.guards/'result.json');assert guard['passed'] and len(guard['cases'])==14
 for n,h in guard['source_hashes'].items():
  if (DIRECTORY/n).exists():assert sha(DIRECTORY/n)==h
 # Concurrent input is tagged by source-frame admission, never by the foreground output loop index.
 assert captures[916]['admitted'] and captures[917]['admitted'] and overlap
 for path in (ROOT/'tools').glob('*373*'):old.PINS[str(path)]=sha(path)
 result=dict(stage=373,analysis_passed=True,continuous_capture_passed=True,candidate=current,baseline372=baseline,paired=pairs,
  fixed_capture_and_initial_ROM_phase=True,source_start_phase_separated=True,completion_intervals=completion,input_display_overlap=overlap,
  unchanged_ARM_PT_LOAD=True,source_payload_hint_and_semantic_plan_exact372=True,shared_compiled_modules=shared,
  guards=guard,whole_MAP=dict(before=before,after=after,delta={k:after[k]-before[k] for k in after},disjoint_self_before=pool[0],disjoint_self_after=pool[1],self_deltas=delta_rows),
  source_ring_bytes=1024,source_shadow_bytes=512,output_queue_slots=2,comb_deficit=after['comb']-15408,deletion_needed_with155reserve=after['comb']-15253,
  full_host_executor_replaced=False,full_plan_decode_replaced=False,first916_capture_fixed=True,
  ARM_size=old.js(ROOT/'analysis/frontier372-verification.json')['ARM_size']['after'],
  replacement_budget=dict(eight_module_pool=sum(pool[1].values()),retained_codec_checker=pool[1][names[0]]+pool[1][names[3]],
   control_pool=sum(pool[1].values())-pool[1][names[0]]-pool[1][names[3]],required_with155reserve=after['comb']-15253,
   all_eight_ceiling=sum(pool[1].values())-(after['comb']-15253),
   retained_codec_control_ceiling=sum(pool[1].values())-pool[1][names[0]]-pool[1][names[3]]-(after['comb']-15253)),
  capture_phase_not_retuned=True,ARM_stack_observed=current['stack_observed'],
  implementation=dict(input_display_contexts=True,source_ring=True,separate_source_shadow=True,shared_D4_CRC8=True,shared_E1_length=True,sequential_header_reader=True,independent_NES_plan_cursor=True,ACK_to_display_hint_lease_gap_removed=True),
  FIT=False,STA=False,physical=False,sustained60fps=False,selected_for_board=False,
  limits=['CPI1/84MHz and IRQ exception/peripheral allocations,not hardware WCET.','Ready-gated ROM requests charged during concurrent source/display,not live NES CPU.','Ordinary65816 trace plus map DMA/display bus models;VBlank firmware unchanged,not full CPU/VBlank proof.','12frames905..916 with10warm and next917 capture;not full71/heavy7/multiple-phase/session/physical validation.','Whole comb still overcapacity;LE/FF reduction does not establish fit.','Host FSM and native plan decoder remain;shared CRC8/length/header progress/cursor are the implemented replacement subset.'],pins=old.PINS)
 a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',newline='\n')
 print(json.dumps({k:result[k] for k in ('paired','input_display_overlap','completion_intervals','whole_MAP','comb_deficit')},indent=2))
if __name__=='__main__':main()
