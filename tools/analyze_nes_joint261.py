# SPDX-License-Identifier: MIT
"""Audit integrated261 evidence; distinguish executed boundaries from whole-path unknowns."""
import argparse,csv,hashlib,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_joint261 import sources
from probe_nes_joint261 import tb,packets


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve();assert not out.exists();out.mkdir(parents=True)
 base=BASE/'probes/nes-joint261';pins={}
 def pin(f):pins[f.relative_to(BASE).as_posix()]=sha(f);return f
 def result(name):return json.loads(pin(base/name/'result.json').read_text())
 joint=result('test05');single=result('single02');cpu=result('cpu02');area=result('map01')
 assert joint['passed'] and joint['frames']==71 and joint['guards']==list(range(1,7))
 assert single['passed'] and single['frames']==3 and cpu['passed'] and cpu['cpu']['ranges']==64 and cpu['cpu']['dma_bytes']==4096
 for name,r in [('test05',joint),('single02',single),('cpu02',cpu),('map01',area)]:
  for n,h in r['rtl_hashes'].items():assert sha(pin(base/name/n))==h and joint['rtl_hashes'][n]==h,(name,n)
  for n,h in r.get('input_hashes',{}).items():assert sha(pin(BASE/n))==h,n
  for f in (base/name).glob('*.log'):pin(f)
 for n,s in sources().items():assert hashlib.sha256(s.encode()).hexdigest()==joint['rtl_hashes'][n],n
 assert pin(base/'test05/joint261_tb.sv').read_text()==tb()
 for case in joint['guards']:
  text=pin(base/f'test05/guard{case:02}/vsim.log').read_text(errors='replace');assert f'PASS JOINT261 NEG={case}' in text and '** Fatal:' not in text
 assert cpu['rom_sha256']==sha(pin(base/'cpu02/joint.sfc'))
 cpu_trace=[list(map(int,line.split(','))) for line in pin(base/'cpu02/cpu-bus.csv').read_text().splitlines()]
 rtl_reads=[list(map(int,line.split(','))) for line in pin(base/'cpu02/rtl-dma.csv').read_text().splitlines()]
 cpu_reads=[r for r in cpu_trace if r[1]==0 and r[2]>=0x400800]
 assert len(cpu_reads)==len(rtl_reads)==4096
 assert [(r[2],r[3]) for r in cpu_reads]==[(r[1],r[2]) for r in rtl_reads]
 assert sum(r[1]==1 and r[2]==0x6050 for r in cpu_trace)==64
 assert sum(r[1]==1 and r[2]==0x6058 for r in cpu_trace)==1
 services=[];ready_clock=None;dma_count=0
 for _,op,address,value,clock in cpu_trace:
  if op==0 and address==0x6040 and value==1:ready_clock=clock;dma_count=0
  if op==0 and address>=0x400800:dma_count+=1
  if op==1 and address==0x6050:
   assert ready_clock is not None and dma_count==64
   services.append(clock-ready_clock);ready_clock=None
 assert len(services)==64
 for n in ['cpu-result.json','cpu-bus.csv','rtl-dma.csv','capture.lua','rpc.do']:pin(base/'cpu02'/n)
 assert area['summary']==pin(base/'map01/output_files/joint.map.summary').read_text() and 'Lite Edition' in area['summary']
 pin(base/'map01/output_files/joint.map.rpt')
 assert area['test_sha256']==sha(pin(base/'test02/result.json'))
 def events(name):
  e={f:dict(receipts=[],output_ms=None,maps_done=None,frame_done=None) for f in range(905,976)}
  for line in pin(base/name/'joint-events.csv').read_text().splitlines():
   kind,f,when,value=line.split(',');f=int(f)
   if kind=='receipt':e[f]['receipts'].append(int(value)/1000) # ps -> ns
   if kind=='maps_done':e[f]['maps_done']=int(when)/1e9
   if kind=='frame_done':e[f]['output_ms']=int(value)/1e9;e[f]['frame_done']=int(when)/1e9
  return e
 je=events('test05');se=events('single02')
 source={int(r['frame']):r for r in csv.DictReader(pin(base/'test05/cycles.csv').open())}
 oldsource={int(r['frame']):r for r in csv.DictReader(pin(BASE/'probes/nes-joint255/test03/cycles.csv').open())}
 # Payload/query/prepare work is unchanged. Shared-bus phase changes can
 # shift CDC wait by a few NES cycles; report, rather than erase, that delta.
 source_deltas=[]
 for f,r in source.items():
  for col in ['prepare','transfer','queries','overlap']:assert r[col]==oldsource[f][col],(f,col)
  source_deltas.append(int(r['total'])-int(oldsource[f]['total']))
 oldrows={r['run']:r for r in csv.DictReader(pin(ROOT/'analysis/batch260-costs.csv').open())}
 rows=[];all_receipts=[]
 for m in joint['map_frames']:
  f=m['frame'];e=je[f];assert len(e['receipts'])==m['ranges'];all_receipts+=e['receipts']
  # Wire benefit from actual packet sizes; this is not total schedule saving.
  pp=[p for p in packets(pin(BASE/f'probes/nes-batch260/arm01/frame{f}.packets')) if p[0]==14]
  values=sum(len(p)-21-3*p[20] for p in pp)
  single_wire=values+23*m['ranges'];assert single_wire>=m['wire_bytes']
  row=dict(frame=f,map_ranges=m['ranges'],batch_packets=m['packets'],batch_wire_bytes=m['wire_bytes'],single_wire_bytes=single_wire,
   wire_saved_ms=(single_wire-m['wire_bytes'])*8/2625000*1000,
   source_actual_rtl_ms=int(source[f]['total'])*45.454/1e6,
   output_with_fixture_service_ms=e['output_ms'],single_output_same_service_ms=se[f]['output_ms'],
   measured_same_service_saving_ms=None if se[f]['output_ms'] is None else se[f]['output_ms']-e['output_ms'],
   validation_tail_including_final_bus_ACK_ms=e['frame_done']-e['maps_done'],
   receipt_core_sum_ms=sum(e['receipts'])/1e6,receipt_core_max_ns=max(e['receipts']),
   receipt_positive_delta_over_old8cycles_ms=sum(max(0,x-8*45.454) for x in e['receipts'])/1e6,
   full_ARM_nonmap_bridge_tile_ROM_VBlank_ms=None,whole_board_LE_margin=None)
  prior=next((r for r in oldrows.values() if int(r['frame'])==f and r['shared_input_output_SPI']=='False' and r['CPI_assumed']=='1' and r['tile_fetch_wait']=='4' and r['conditional_source_plus_output_ms']),None)
  row['prior260_source_plus_output_model_ms']=None if prior is None else float(prior['conditional_source_plus_output_ms'])
  row['tail_added_sensitivity_ms']=None if prior is None else float(prior['conditional_source_plus_output_ms'])+row['validation_tail_including_final_bus_ACK_ms']
  # The cold actual65816 path exposes ~900 clocks beyond nominal DMA.
  # This serial sum of +400 clocks/range is sensitivity, not a retimed path:
  # some work can overlap SPI, and the old model already charges token writes.
  row['setup500_to900_serial_sensitivity_extra_ms']=m['ranges']*400/21477272.727*1000
  row['prior_plus_tail_plus900_sensitivity_ms']=None if prior is None else row['tail_added_sensitivity_ms']+row['setup500_to900_serial_sensitivity_extra_ms']
  rows.append(row)
 shared_sensitivity=[]
 for name in ['bus954','bus963','bus970','bus-cpi2']:
  old=oldrows[name];row=next(r for r in rows if r['frame']==int(old['frame']))
  value=float(old['ARM_completion_model_ms'])+row['validation_tail_including_final_bus_ACK_ms']+row['setup500_to900_serial_sensitivity_extra_ms']
  shared_sensitivity.append(dict(prior_run=name,prior_ms=float(old['ARM_completion_model_ms']),tail_plus_setup900_serial_sensitivity_ms=value,remaining_to_60Hz_ms=1000/60-value,physical_bound=False,full_source_ARM_binding=False))
 with (out/'costs.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys(),lineterminator='\n');w.writeheader();w.writerows(rows)
 report=dict(passed=True,stage='NES261',frames=71,map_ranges=sum(r['map_ranges'] for r in rows),batch_packets=sum(r['batch_packets'] for r in rows),
  source_bytes=joint['source_bytes'],source_cycle_delta255=[min(source_deltas),max(source_deltas)],guards=joint['guards'],actual_CPU=cpu['cpu'],rom_body_bytes=cpu['rom_body_bytes'],
  actual_CPU_service=dict(scope='cold64B ranges, ready status to consume; logical RPC polling outside this interval excluded',ranges=64,master_clocks_min=min(services),master_clocks_max=max(services),nominal_DMA_clocks=512,beyond_nominal_DMA_min=min(services)-512,beyond_nominal_DMA_max=max(services)-512,includes_refresh_and_alignment=True),
  receipt_core_ns=[min(all_receipts),max(all_receipts)],
  integrated_MAP=dict(LE=7141,comb=5665,FF=2788,RAM_bits=90368,whole_board=False,FIT=False,STA=False),
  replacement_ledger=dict(old_excluding_lease=dict(comb=3336,FF=2084,RAM_bits=98560),new_excluding_lease_and_top=dict(comb=5465,FF=2689,RAM_bits=90368),arithmetic_delta=dict(comb=2129,FF=605,RAM_bits=-8192),same_synthesis_boundary=False,proven_whole_LE_reclaim=0),
  prior260_shared_SPI_CPI2_ms=float(oldrows['bus-cpi2']['ARM_completion_model_ms']),
  CPI2_prior_plus_entire261_tail_sensitivity_ms=float(oldrows['bus-cpi2']['ARM_completion_model_ms'])+next(r['validation_tail_including_final_bus_ACK_ms'] for r in rows if r['frame']==954),
  shared_SPI_serial_sensitivity=shared_sensitivity,
  full_path_ms=None,physical60fps=False,P2_selected=False,
  limitations=['ARM260 batch descriptors/value/splits replayed; sequence/token rebound at fixture boundary','non-map stream and H2/context/check producers are fixtures; their core validation is real','ARM H2 late vs core context-before-begin unresolved','source SPI fixture driver, not full ARM N5/planner/RUN/IRQ','RPC CPU and RTL timelines independent','tile192/ROM competition and full command/PPU path open','MAP boundary excludes retained whole-board logic'],
  same_service_reference=rows[:3],heavy=[r for r in rows if r['frame'] in [952,954,955,962,963,968,970]],input_hashes=pins)
 (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ['input_hashes','heavy','same_service_reference']},indent=2))

if __name__=='__main__':main()
