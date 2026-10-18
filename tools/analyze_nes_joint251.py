# SPDX-License-Identifier: MIT
"""Measured phase RAM/ARM object comparison and conditional timing sensitivity."""
from pathlib import Path
import argparse,csv,json,re,shutil
from nes_delta231 import ROOT,BASE,sha

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);pins={};P=BASE/'probes/nes-joint251'
 def pin(f):pins[f.relative_to(BASE).as_posix()]=sha(f);return f
 def read(f):return json.loads(pin(f).read_text())
 def rows(f):return list(csv.DictReader(pin(f).open()))
 old=read(BASE/'probes/nes-joint250/analysis02/result.json');phase=read(P/'phase03/result.json');mapped=read(P/'map02/result.json');arm=read(P/'arm03/result.json')
 for r in (phase,mapped,arm):
  assert r['passed']
  for n,h in r['input_hashes'].items():assert sha(pin(BASE/n))==h,n
 assert phase['rtl_hashes']==mapped['rtl_hashes']
 for n,h in phase['rtl_hashes'].items():assert sha(pin(P/'phase03'/n))==sha(pin(P/'map02'/n))==h
 sc=rows(P/'phase03/cycles.csv')[:71];ref=rows(BASE/'probes/nes-joint249/blocktest03/cycles.csv')[:71]
 assert [r['prepare'] for r in sc]==[r['prepare'] for r in ref]
 rc={int(r['frame']):int(r['cycles']) for r in rows(P/'phase03/receipt-cycles.csv')[:71]}
 oldrc={int(r['frame']):int(r['cycles']) for r in rows(BASE/'probes/nes-joint250/receipt02/cycles.csv')}
 assert rc==oldrc
 def area(s):
  return {k:int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',s).group(1).replace(',','')) for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('bits','Total memory bits')]}
 before=area(old['area']['summary']);after=area(mapped['summary'])
 resultrows=[]
 # Two clock allocations cover phase handoff, conservatively serial; no claim
 # that cross-frame overlap in the eventual collector is preserved.
 handoff=2/22000
 for r in old['rows']:
  for cycles in (0,8000,32000):
   for cert in (0,32):
    total=r['total_ms']-r['validate_ms']+handoff+cycles/84000+cert*8/2625
    resultrows.append(dict(frame=r['frame'],setup=r['map_setup_clocks'],retained_policy=r['retained_policy'],arm_cycles_allocated=cycles,extra_binding_bytes=cert,total_ms=total,residual_ms=1000/60-total,removed_snes_ms=r['validate_ms'],phase_allocated_ms=handoff,arm_allocated_ms=cycles/84000,binding_wire_allocated_ms=cert*8/2625))
 summaries=[]
 for setup in (500,1000):
  for mode in ('command_tail','only_bitmap_removed'):
   for cycles in (0,8000,32000):
    for cert in (0,32):
     rr=[r for r in resultrows if (r['setup'],r['retained_policy'],r['arm_cycles_allocated'],r['extra_binding_bytes'])==(setup,mode,cycles,cert)]
     summaries.append(dict(setup=setup,retained_policy=mode,arm_cycles_allocated=cycles,extra_binding_bytes=cert,max_ms=max(r['total_ms'] for r in rr),min_residual_ms=min(r['residual_ms'] for r in rr),over=[r['frame'] for r in rr if r['residual_ms']<0],worst_frame=max(rr,key=lambda r:r['total_ms'])['frame']))
 for n in ('nes_phase251.py','probe_nes_phase251.py','nes_hdma251.c','probe_nes_hdma251.py','analyze_nes_joint251.py'):pin(ROOT/'tools'/n)
 for n in ('config-mk3-stm32','stm32f4xx/clock.c','nes_native_sink165.c','nes_planner211.c'):pin(BASE/'probes/nes-runtime233/arm01/src'/n)
 for n in ('tools/nes_client181.py','tools/nes_block249_rtl.py','tools/nes_receipt250.py'):pin(ROOT/n)
 rawjson=dict(passed=True,stage=251,scope=__doc__,phase={k:v for k,v in phase.items() if k!='input_hashes'},arm={k:v for k,v in arm.items() if k not in ('input_hashes','frames_detail')},area_before=before,area_after=after,area_delta={k:after[k]-before[k] for k in before},
  scratch_before='512x8 TDP plus1024x8 single port',scratch_after='one1024x8 TDP;source512..1023,validity0..331,temp332..753',inferred_RAM_instance_reduction=1,placed_M9K_recovery_proven=False,
  source_prepare_cycles_unchanged=True,receipt_cycles_unchanged=True,phase_handoff_allocation_cycles=2,initial_clear_cycles=754,
  arm_scroll_runs=[min(r['scroll_runs'] for r in arm['frames_detail']),max(r['scroll_runs'] for r in arm['frames_detail'])],arm_patch_runs=[min(r['patch_runs'] for r in arm['frames_detail']),max(r['patch_runs'] for r in arm['frames_detail'])],
  incremental_break_even_arm_cycles_32B=min(r['validate_ms']-handoff-32*8/2625 for r in old['rows'])*84000,
  summaries=summaries,rows=resultrows,input_hashes=pins,limitations=[
   'Phase RAM tested on parsed fixture interfaces,not collector/query/SPI/parser/CDC or final display transport.',
   'Source and receipt FSM/datapath remain separate;parent244comb includes logic moved across hierarchy,not pure new overhead.',
   'One inferred scratch RAM eliminated;wholeboard55/56M9K is arithmetic scenario,not placement.',
   'Host C execution and Cortex-M4 object measured;ARM hardware cycles/full RUN/IRQ/certificate binding not measured.',
   '8000/32000cycles and0/32extra wire bytes are sensitivity allocations,not bound/implemented certificate.',
   'Moving SNES validate181 is counterfactual until immutable candidate plus end-to-end receipt binding exists.',
   'Remaining SNES command/ordinary DMA,ARM planning/query/polls/gaps/VBlank share residual;no60fps/FIT/STA/package approval.'])
 (d/'result.json').write_text(json.dumps(rawjson,indent=2)+'\n')
 public={k:v for k,v in rawjson.items() if k not in ('input_hashes','rows')};public.update(input_count=len(pins),private_result_sha256=sha(d/'result.json'))
 (d/'summary.json').write_text(json.dumps(public,indent=2)+'\n')
 with (d/'schedules.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(resultrows[0]),lineterminator='\n');w.writeheader();w.writerows(resultrows)
 shutil.copyfile(__file__,d/'analyzer.py')
 print(json.dumps(dict(area=after,delta=rawjson['area_delta'],break_even_cycles=rawjson['incremental_break_even_arm_cycles_32B'],selected=[r for r in summaries if r['setup']==500 and r['retained_policy']=='command_tail']),indent=2))
if __name__=='__main__':main()
