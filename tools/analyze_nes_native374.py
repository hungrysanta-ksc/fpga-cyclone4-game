# SPDX-License-Identifier: MIT
"""Match native374 byte ABI,actual ARM schedules,independent receipts and one M9K."""
import argparse,json,re
from pathlib import Path
import analyze_nes_source368 as old
from analyze_nes_receipt335 import load_image
from analyze_nes_dual373 import self_costs
from nes_dual373 import COMMON
from nes_bg295 import unbatch
from nes_delta231 import ROOT,BASE,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--map',type=Path,required=True);p.add_argument('--guards',type=Path,required=True);p.add_argument('--lifetime',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.run.resolve();board=a.map.resolve();ref=BASE/'probes/nes-dual373/joint03';bm=BASE/'probes/nes-dual373/map03'
 current=old.measure(d,916,0);before=old.measure(ref,916,0);ev=old.events(d);be=old.events(ref)
 assert load_image(d/'output.elf')==load_image(ref/'output.elf')
 pairs=[]
 for x,y in zip(current['rows'],before['rows']):
  f=x['frame'];assert f==y['frame'];same=(x['start_ps'],x['start_ROM_cycle'])==(y['start_ps'],y['start_ROM_cycle'])
  if 907<=f<=914:assert same
  ta=old.js(d/f'arm{f}.json')['transfers'];tb=old.js(ref/f'arm{f}.json')['transfers']
  # Compression and causal hint inputs remain identical;status polling may vary.
  payload=lambda t:[i['rx'] for i in t if i.get('source_phase367')==2 and i['rx']]
  hints=lambda t:[i['tx'] for i in t if i['tx'].startswith('ea') and len(i['tx'])==56]
  assert payload(ta)==payload(tb) and hints(ta)==hints(tb)
  pa=d/f'actual-plans293-{f}.bin';pb=ref/f'actual-plans293-{f}.bin';old.PINS[str(pa)]=sha(pa);old.PINS[str(pb)]=sha(pb)
  assert pa.read_bytes()==pb.read_bytes() and unbatch(pa.read_bytes())==unbatch(pb.read_bytes())
  old_data_clocks=2*sum(map(len,unbatch(pa.read_bytes())));records=len(unbatch(pa.read_bytes()))
  pairs.append(dict(frame=f,before_ms=y['processing_ms'],after_ms=x['processing_ms'],delta_ms=x['processing_ms']-y['processing_ms'],same_source_start_ROM_cycle=same,
   before_materialized_ms=y['materialized_ms'],after_materialized_ms=x['materialized_ms'],before_BG=y.get('BG'),after_BG=x.get('BG'),before_OBJ=y.get('OBJ'),after_OBJ=x.get('OBJ'),
   before_SPI=y['total_SPI_bytes'],after_SPI=x['total_SPI_bytes'],plan_records=records,old_data_read_clocks=old_data_clocks,native_data_read_clocks=9*records,data_read_clock_allocation_delta=9*records-old_data_clocks))
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
 canonical=ROOT/'src/fpga/nes_native374/nes_plan_batch206.sv';assert sha(canonical)==sha(d/canonical.name)==sha(board/canonical.name)
 guards=old.js(a.guards/'result.json');life=old.js(a.lifetime/'result.json');context=old.js(BASE/'probes/nes-native374/context02.json')
 retained=old.js(BASE/'probes/nes-dual373/guards03/result.json')
 for n,h in retained['source_hashes'].items():
  if (d/n).exists():assert sha(d/n)==h
 assert guards['passed'] and guards['valid']==36 and guards['malformed']==8 and guards['STOP']==8 and guards['max_wire_bytes']==512 and guards['max_records']==16
 assert life['passed'] and len(life['cases'])==6
 assert guards['actual_inputs']['nes_plan_batch206.sv']==life['actual_inputs']['nes_plan_batch206.sv']==sha(canonical)
 old.PINS[str(board/'map.log')]=sha(board/'map.log');report=(board/'map.log').read_bytes().decode('ascii',errors='replace');assert 'nes_plan_ram374:payload|altsyncram:ram' in report
 # Explicit one256x32 primitive. No split byte-lane or FF implementation selected.
 assert '.width_a(32),.widthad_a(8),.numwords_a(256)' in canonical.read_text() and '.width_byteena_a(4)' in canonical.read_text()
 assert 'reg [31:0] payload[' not in canonical.read_text()
 ram_rows=[k for k in costs[1] if 'nes_plan_batch206:transport|' in k and k.endswith('|altsyncram:ram')]
 assert len(ram_rows)==1
 completions=[dict(frame=x['frame'],interval_ms=(int(old.event(ev,'frame_done',x['frame'])[2])-int(old.event(ev,'frame_done',x['frame']-1)[2]))/1e9) for x in current['rows'][3:]]
 names=['nes_core257:encoder','nes_transport257:transport','nes_spi270:spi_front270','nes_validator278:validator','nes_output260:flow','nes_plan_batch206:transport','nes_plan_spi200:endpoint','nes_queue260:queue']
 pools=[{n:next(v['comb'] for k,v in c.items() if k.endswith('|'+n)) for n in names} for c in costs]
 for f in (ROOT/'tools').glob('*374*'):old.PINS[str(f)]=sha(f)
 result=dict(stage=374,analysis_passed=True,continuous_capture_passed=True,candidate=current,baseline373=before,paired=pairs,
  byte_identical_wire_plan=True,unchanged_ARM_PT_LOAD=True,shared_compiled_modules=shared,guards=guards,lifetime=life,
  retained_source_context_guards=retained,context_port_audit=context,single_native_M9K=True,wire_compressed=True,native_record_bytes=32,native_word_bits=32,host_init_clocks_per_record=8,
  whole_MAP=dict(before=prior,after=after,delta={k:after[k]-prior[k] for k in after},disjoint_self_before=pools[0],disjoint_self_after=pools[1]),
  comb_deficit=after['comb']-15408,required_with155reserve=after['comb']-15253,completion_intervals=completions,
  NES_operand_decoder_replaced=True,host_shared_executor_replaced=False,selected_default_RTL=373,selected_for_board=False,
  FIT=False,STA=False,physical=False,sustained60fps=False,
  limits=['Compiled372 M4 at CPI1/84MHz and explicit IRQ/peripheral allocations,not hardware WCET.','Ready-gated ROM stress;ordinary65816 trace plus map DMA/display models,not fullCPU/VBlank/liveNES.','12frames905..916,next917 capture;not71/heavy7/multiple phase/session/physical validation.','Native byte default writes must finish before next byte;tested actual2.625MHzSPI and32host-clock unit spacing.','Vendor model warns DONT_CARE mixed-port reads assume OLD_DATA;bank/decoded lifetime tests ensure no consumed response relies on a collision.','No combinational-area saving after retaining one M9K;host decoder remains independent of host output executor.'],pins=old.PINS)
 a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',newline='\n');print(json.dumps({k:result[k] for k in ('paired','whole_MAP','comb_deficit','completion_intervals')},indent=2))
if __name__=='__main__':main()
