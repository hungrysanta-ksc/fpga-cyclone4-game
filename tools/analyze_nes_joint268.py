# SPDX-License-Identifier: MIT
"""Whole-cost comparison of actual65816 zero DMA/reuse and live267 schedule.

Control-sharing values are explicitly optimistic accounting/protocol scenarios,
not synthesized replacements. The unchanged core is retimed, and one new Lite MAP removes a legacy endpoint.
"""
from pathlib import Path
import argparse,collections,csv,hashlib,json,re
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile
from guard_nes_plan268 import decode


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--guard',default='plan-guard01');a=p.parse_args()
 b=a.base.resolve();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);pins={}
 def pin(f):
  key=f.relative_to(b).as_posix() if f.is_relative_to(b) else f.relative_to(BASE).as_posix()
  pins[key]=sha(f);return f
 def read(f):return json.loads(pin(f).read_text(encoding='utf-8'))
 def events(folder):return list(csv.reader(pin(folder/'joint-events.csv').open()))
 def times(folder):return {int(x[1]):int(x[3])/1e9 for x in events(folder) if x[0]=='frame_done'}
 for name in ['analyze_nes_joint268.py','guard_nes_plan268.py','probe_nes_ordinary268.py','map_nes_cleanup268.py']:pin(ROOT/'tools'/name)
 oldbase=BASE/'probes/nes-joint267';old=read(ROOT/'analysis/joint267-verification.json')
 oldrows={int(x['frame']):x for x in csv.DictReader(pin(ROOT/'analysis/joint267-costs.csv').open())}
 selected=['cpu-reuse05','cpu-dma05','cpu-guards03','joint-reuse01','joint-dma01','window-reuse01',a.guard,'board01','rompad-guard01']
 results={name:read(b/name/'result.json') for name in selected}
 assert all(r['passed'] for r in results.values())
 reference=read(oldbase/'joint04/result.json')
 loaded={}
 for folder,r in [(oldbase/'joint04',reference)]+[(b/n,results[n]) for n in ['joint-reuse01','joint-dma01','window-reuse01']]:
  assert r['rtl_hashes']==reference['rtl_hashes']
  for name,h in r['rtl_hashes'].items():assert sha(pin(folder/name))==h
  with pin(folder/'output.elf').open('rb') as f:
   loaded[folder.name]=[(s['p_vaddr'],s['p_memsz'],s['p_flags'],hashlib.sha256(s.data()).hexdigest()) for s in ELFFile(f).iter_segments() if s['p_type']=='PT_LOAD']
 assert all(v==loaded['joint04'] for v in loaded.values())
 # Relocate the zero constant into the existing program-ROM decode. Queue
 # bus timestamps are identical, so the already executed RTL replay still applies.
 for mode in ['reuse','dma']:
  for name in ['bus.csv','timing.csv','packets.hex']:
   assert pin(b/f'cpu-{mode}04'/name).read_bytes()==pin(b/f'cpu-{mode}05'/name).read_bytes()
 assert pin(b/'cpu-reuse03/bus.csv').read_bytes()==pin(b/'cpu-reuse05/bus.csv').read_bytes()
 assert results['cpu-reuse05']['existing165_ROM_decode']
 assert results['board01']['changed_hashes']==results['rompad-guard01']['changed_hashes']
 for name,h in results['board01']['changed_hashes'].items():assert sha(pin(b/'board01'/name))==h==sha(pin(b/'rompad-guard01'/name))
 for n in ['cpu-reuse05','cpu-dma05']:
  r=results[n];assert r['CPU']['commands']==522 and r['CPU']['output_bytes']==128041
  assert pin(b/n/'packets.hex').read_bytes()==pin(oldbase/'cpu05/packets.hex').read_bytes()
 assert results['cpu-reuse05']['CPU']['zero_DMA_fills']==2
 assert results['cpu-dma05']['CPU']['zero_DMA_fills']==71
 assert results['cpu-guards03']['CPU']['commands']==33 and results['cpu-guards03']['CPU']['zero_DMA_fills']==10
 command_costs={}
 for name,folder in [('prior267',oldbase/'cpu05'),('dma',b/'cpu-dma05'),('reuse',b/'cpu-reuse05')]:
  cr=[{k:int(v) for k,v in x.items()} for x in csv.DictReader(pin(folder/'timing.csv').open())]
  command_costs[name]=[]
  for op in sorted({x['op'] for x in cr}):
   group=[x for x in cr if x['op']==op];warm=[x for x in group if x['serial']>=3]
   command_costs[name].append(dict(op=op,commands=len(group),output_bytes=sum(x['output_bytes'] for x in group),
    min_ms=min(x['total_clocks'] for x in group)/21477.272727,max_ms=max(x['total_clocks'] for x in group)/21477.272727,
    warm_min_ms=min(x['total_clocks'] for x in warm)/21477.272727,warm_max_ms=max(x['total_clocks'] for x in warm)/21477.272727,
    PPU_DMA_bytes=sum(x['dma_bytes'] for x in group)))
 q=b/'joint-reuse01';r=results[q.name];ev=events(q);done=times(q);arm={x['frame']:x for x in r['ARM']['frames']}
 assert len(done)==71 and r['frames']==71 and r['actual_tile_ROM'] and r['actual_SNES_bus_trace_replayed']
 assert sum(x[0]=='cpu267' for x in ev)==522 and sum(x[0]=='receipt' for x in ev)==2069
 assert max(int(x[2]) for x in ev if x[0]=='credits')==4
 assert pin(q/'blocks.txt').read_bytes()==pin(oldbase/'joint04/blocks.txt').read_bytes()
 source={int(x['frame']):x for x in csv.DictReader(pin(q/'cycles.csv').open())}
 rows=[];previous_wire=previous_output=0
 for f in range(905,976):
  assert pin(q/f'all{f}.hex').read_bytes()==pin(oldbase/f'joint04/all{f}.hex').read_bytes()
  count=collections.Counter();wire=collections.Counter()
  for x in ev:
   if x[0]=='arm267' and int(x[1])==f:count[f'{int(x[2]):02x}']+=1;wire[f'{int(x[2]):02x}']+=int(x[3])
  assert sum(wire.values())==arm[f]['SPI_bytes']
  cumulative=int(source[f]['wirebytes_cumulative']);source_wire=cumulative-previous_wire-previous_output
  previous_wire=cumulative;previous_output=arm[f]['SPI_bytes'];sm=int(source[f]['total'])*45.454/1e6
  total=sm+done[f];prior=float(oldrows[f]['diagnostic_serial_ms'])
  rows.append(dict(frame=f,source_ms=sm,output_schedule_ms=done[f],diagnostic_serial_ms=total,prior_serial_ms=prior,
   serial_saved_ms=prior-total,remaining_to_60_ms=max(0,total-1000/60),budget_headroom_ms=1000/60-total,
   ARM_instructions=arm[f]['instructions'],SPI_bytes=arm[f]['SPI_bytes'],source_SPI_bytes=source_wire,
   shared_SPI_bytes=source_wire+arm[f]['SPI_bytes'],shared_SPI_wire_ms=(source_wire+arm[f]['SPI_bytes'])*8/2625,
   non_wire_elapsed_ms=total-(source_wire+arm[f]['SPI_bytes'])*8/2625,
   E0_polls=count['e0'],E8_polls=count['e8'],E9_batches=count['e9'],EA_retire=count['ea'],
   plan_SPI_bytes=wire['e8']+wire['e9']+wire['ea'],prior_E0_polls=int(oldrows[f]['E0_polls']),
   shared_envelope_frozen_transcript_wire_saving_B=wire['e8']+wire['ea']-11*count['e9']))
 with (d/'costs.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 warm=rows[2:];worst=max(warm,key=lambda x:x['diagnostic_serial_ms']);budget=1000/60
 paired=[]
 for f in range(905,908):
  paired.append(dict(frame=f,prior_output_ms=float(oldrows[f]['output_schedule_ms']),DMA_output_ms=times(b/'joint-dma01')[f],
   reuse_output_ms=done[f],prior_restricted_ROM_ms=times(oldbase/'window01')[f],reuse_restricted_ROM_ms=times(b/'window-reuse01')[f]))
  ws=next(x for x in csv.DictReader(pin(b/'window-reuse01/cycles.csv').open()) if int(x['frame'])==f)
  paired[-1]['restricted_source_ms']=int(ws['total'])*45.454/1e6
  paired[-1]['restricted_diagnostic_serial_ms']=paired[-1]['restricted_source_ms']+paired[-1]['reuse_restricted_ROM_ms']
 # Non-overlapping hierarchy entries; this is not a net whole-board reclaim.
 report=pin(b/'board01/output_files/board.map.rpt').read_text(errors='replace');hierarchy={}
 for line in report.splitlines():
  fields=[v.strip() for v in line.split(';')]
  if len(fields)>10 and fields[1] in ['|nes_queue260:queue|','|nes_plan_spi200:endpoint|','|nes_plan_batch206:transport|']:
   hierarchy[fields[1]]={k:int(re.match(r'\d+',v).group()) for k,v in zip(['comb','FF','RAM_bits'],fields[2:5])}
 assert len(hierarchy)==3
 envelope=sum(x['comb'] for x in hierarchy.values())
 prior_area=old['MAP']['replacement266'];summary=results['board01']['summary'];assert 'Lite Edition' in summary
 area={k:int(re.search(pattern+r'\s*:\s*([\d,]+)',summary).group(1).replace(',','')) for k,pattern in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
 deficit=area['comb']-15408;assert deficit>0 and area['RAM_bits']==prior_area['RAM_bits']-8192
 assert not results['board01']['undriven_outputs']
 legacy={}
 for line in report.splitlines():
  fields=[v.strip() for v in line.split(';')]
  if len(fields)>10 and fields[1] in ['|nes_sink_bridge165:sink|','|nes_sink_bus165:bus|']:
   legacy[fields[1]]={k:int(re.match(r'\d+',v).group()) for k,v in zip(['comb','FF','RAM_bits'],fields[2:5])}
 assert legacy['|nes_sink_bridge165:sink|']['RAM_bits']==32768
 assert '|nes_sink_spi165:endpoint|' not in report
 plans=0;batches=0;payload=0;max_payload=0;witness=[]
 for gen in range(1,72):
  data=pin(oldbase/f'plans01/plans{gen}.bin').read_bytes();at=0;bi=0
  while at<len(data):
   n=int.from_bytes(data[at:at+2],'little');count=data[at+2];raw=data[at+3:at+3+n];at+=3+n;bi+=1
   decoded=decode(raw);assert len(decoded)==count and all(x['generation']==gen for x in decoded)
   plans+=count;batches+=1;payload+=n;max_payload=max(max_payload,n)
   breaks=sum((x['kind']==1)!=(y['kind']==1) or y['slot']!=x['slot']+1 for x,y in zip(decoded,decoded[1:]))
   if breaks>=4:witness.append(dict(frame=gen+904,batch=bi,breaks=breaks,plans=decoded))
 assert (plans,batches,payload,max_payload)==(598,88,4113,113)
 guard=results[a.guard];assert guard['frame']==949 and any('PASS HELD_HEAD_BLOCKED' in x for x in guard['logs']) and any('PASS COPY_RELEASE' in x for x in guard['logs'])
 rom_ev=events(b/'window-reuse01');rom_wait=[list(map(int,x[1:])) for x in rom_ev if x[0]=='romwait267'];assert len(rom_wait)==3 and all(x[-1]>0 for x in rom_wait)
 result=dict(passed=True,stage='NES268',scope=__doc__,selected=selected,frames=71,command_costs=command_costs,paired=paired,
  warm_max_serial=worst,warm_max_output=max(warm,key=lambda x:x['output_schedule_ms']),warm_over_serial=sum(x['diagnostic_serial_ms']>budget for x in warm),
  warm_wire_over=[x for x in warm if x['shared_SPI_wire_ms']>budget],restricted_ROM_waits=rom_wait,
  totals={k:sum(x[k] for x in rows) for k in ['ARM_instructions','SPI_bytes','source_SPI_bytes','shared_SPI_bytes','E0_polls','E8_polls','E9_batches','EA_retire','plan_SPI_bytes']},
  prior_totals=old['ARM'],
  CPU=dict(prior_code_bytes=374,DMA_code_bytes=results['cpu-dma05']['rom_body_bytes'],reuse_code_bytes=results['cpu-reuse05']['rom_body_bytes'],
   ROM_constant_bytes=1,zero_source=results['cpu-reuse05']['zero_source'],validity_WRAM_bytes=2,bank_index_scratch_bytes=2,total_extra_WRAM_bytes=4,normal_commands=522,output_bytes=128041,normal_reuse_fills=2,normal_skips=69,
   guards=results['cpu-guards03']['CPU'],common_STOP_binding=False,all_write_owners_bound=False),
  ARM=dict(text=3104,bss=604,observed_stack=r['ARM']['stack_observed'],IRQ_bodies=len(r['ARM']['IRQ_cases']),CPI=1,loaded_segments=loaded,
   full_RUN=False,hardware_cycles=False,NVIC=False),
  MAP=dict(prior267=prior_area,cleanup268=area,new_run=True,core_RTL_unchanged=True,board_cleanup_only=True,delta={k:area[k]-prior_area[k] for k in area},legacy_ROM_pad=legacy,ROM_pad_guard=results['rompad-guard01'],comb_capacity=15408,comb_deficit=deficit,minimum_reduction_percent=100*deficit/area['comb'],
   FIT=False,STA=False,functional_board_glue_verified=False,program_link_changed=False),
  controls=dict(hierarchy=hierarchy,identified_comb=envelope,zero_cost_replacement_outside_deficit=deficit-envelope,
   accounting_only=True,net_reclaim_proven=0,new_RTL=False,new_MAP=False,plan_RAM_bits_retained_by_copy_policy=8192,
   replacement_sensitivity=[dict(new_controller_comb=c,required_additional_outside_reduction=deficit-envelope+c) for c in [0,400,600,800,1000]],
   plans=plans,plan_batches=batches,END_batches=71,max_plan_payload=max_payload,blocked_witness=guard['logs'],actual_plan_break_batches=witness,
   frozen_transcript_wire_saving_B=sum(x['shared_envelope_frozen_transcript_wire_saving_B'] for x in rows),
   optional_common_generation_bytes=2*(plans+71),wire_projection_is_timing=False),
  remaining=dict(diagnostic_ms=max(0,worst['diagnostic_serial_ms']-budget),current_time_reduction_percent=100*max(0,worst['diagnostic_serial_ms']-budget)/worst['diagnostic_serial_ms'],
   comb=deficit,restricted_warm_sample_ms=paired[-1]['restricted_diagnostic_serial_ms'],restricted_warm_sample_gap_ms=max(0,paired[-1]['restricted_diagnostic_serial_ms']-budget),full_path_ms=None,extra_full_RUN_VBlank_mapper_margin_ms=None,physical60fps=False),
  P2_selected=False,whole_MAP_LE_saved=prior_area['LE']-area['LE'],limitations=[
   'Actual65816 ordinary command kernel uses forced blank; live VBlank, map/tile DMA and final display remain outside this CPU run.',
   'Live ARM serializer/refill uses instruction CPI1; full input/planner/NVIC/IRQ entry/exit and hardware SRAM margin are not measured.',
   'Actual ROM/cache/priority RTL uses synthetic core requests and qualified slot policy; no live NES core or universal worst-case bound.',
   'Bank reuse validity covers this kernel write owner and two cold banks; board common STOP/external writers are not bound.',
   'Whole-board Lite MAP removes the duplicate legacy E0/E1 endpoint and preserves local ROM/pad; no whole-board functional/CDC/STA or complete firmware link qualification.',
   'Unified queue head policies are liveness experiments on retained decoder/staging RTL; no unified controller implementation or area gain is claimed.',
   'Frozen transcript wire projection excludes new controller/ARM polling schedule costs and must not be added to measured CPU gains.'
  ],artifact_hashes=pins)
 (d/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps(dict(passed=True,warm_max_ms=worst['diagnostic_serial_ms'],remaining_ms=result['remaining']['diagnostic_ms'],warm_over=result['warm_over_serial'],comb_deficit=deficit)))


if __name__=='__main__':main()
