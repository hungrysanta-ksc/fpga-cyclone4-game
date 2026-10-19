# SPDX-License-Identifier: MIT
"""Compare retimed ARM/ROM/65816-trace schedules and whole-board Lite MAP.

No CPI, synthetic ROM slot policy, or bus replay is a physical timing bound.
The archive manifest separately covers raw evidence, including rejected runs.
"""
import argparse,collections,csv,hashlib,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--contention');a=p.parse_args()
 b=a.base.resolve();out=a.out.resolve();assert not out.exists();out.mkdir(parents=True);pins={}
 def pin(path):
  key=path.relative_to(b).as_posix() if path.is_relative_to(b) else path.relative_to(BASE).as_posix()
  pins[key]=sha(path);return path
 def read(path):return json.loads(pin(path).read_text(encoding='utf-8'))
 def events(name):return list(csv.reader(pin(b/name/'joint-events.csv').open()))
 def timing(name):return {int(r[1]):int(r[3])/1e9 for r in events(name) if r[0]=='frame_done'}
 names=['joint03','joint04','compare01','window01','board02','board26501','cpu04','cpu05','plans01']
 res={n:read(b/n/'result.json') for n in names}
 for n,r in res.items():
  assert r['passed'],n
  for f,h in r.get('rtl_hashes',{}).items():assert sha(pin(b/n/f))==h,(n,f)
  for f,h in r.get('changed_hashes',{}).items():assert sha(pin(b/n/f))==h,(n,f)
  for f in (b/n).glob('*.log'):pin(f)
 assert res['joint04']['frames']==71 and res['joint04']['actual_tile_ROM']
 assert res['joint03']['rtl_hashes']==res['joint04']['rtl_hashes']==res['window01']['rtl_hashes']
 loaded_ARM={}
 for n in ['joint03','joint04','compare01','window01']:
  path=pin(b/n/'output.elf');assert sha(path)==res[n]['ELF_sha256']
  with path.open('rb') as f:
   elf=ELFFile(f)
   loaded_ARM[n]=[dict(address=s['p_vaddr'],memory_bytes=s['p_memsz'],flags=s['p_flags'],sha256=hashlib.sha256(s.data()).hexdigest()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
 assert all(x==loaded_ARM['joint03'] for x in loaded_ARM.values()) # Non-loaded .strtab contains temporary object filenames.
 assert res['compare01']['baseline265'] and res['window01']['ROM_window']==1
 assert res['board02']['test_sha256']==sha(b/'joint03/result.json')
 assert res['board26501']['test_sha256']==sha(b/'compare01/result.json')
 for n in ['bus.csv','ordinary.sfc']:
  assert pin(b/'cpu04'/n).read_bytes()==pin(b/'cpu05'/n).read_bytes(),n
 assert res['cpu05']['CPU']==dict(passed=True,commands=522,output_bytes=128041)
 cpurows=[{k:int(v) for k,v in row.items()} for row in csv.DictReader(pin(b/'cpu05/timing.csv').open())]
 assert min(x['read_clocks'] for x in cpurows)>=0
 command_costs=[]
 for op in sorted({x['op'] for x in cpurows}):
  group=[x for x in cpurows if x['op']==op]
  command_costs.append(dict(op=op,commands=len(group),output_bytes=sum(x['output_bytes'] for x in group),
   DMA_bytes=sum(x['dma_bytes'] for x in group),min_service_ms=min(x['total_clocks'] for x in group)/21477.272727,
   max_service_ms=max(x['total_clocks'] for x in group)/21477.272727))
 irq=read(BASE/'probes/nes-joint267/irq01/result.json')
 assert irq['passed'] and len(irq['cases'])==22
 assert sha(pin(BASE/'probes/nes-runtime233/arm01/src/obj-nes-100/sd2snes.elf'))==irq['ELF_sha256']
 old=read(ROOT/'analysis/joint266-verification.json')
 src={int(r['frame']):r for r in csv.DictReader(pin(b/'joint04/cycles.csv').open())}
 ev=events('joint04');done=timing('joint04');arm={r['frame']:r for r in res['joint04']['ARM']['frames']}
 consumers={int(r[1]):list(map(int,r[2:])) for r in ev if r[0]=='consumer'}
 assert len(done)==71 and sum(r[0]=='receipt' for r in ev)==2069
 assert sum(r[0]=='cpu267' for r in ev)==522
 assert len([r for r in ev if r[0]=='credits'])==71 and max(int(r[2]) for r in ev if r[0]=='credits')==4
 assert pin(b/'joint04/blocks.txt').read_bytes()==pin(BASE/'probes/nes-joint266/test03/blocks.txt').read_bytes()
 rows=[];previous_wire=0;previous_output_wire=0
 for f in range(905,976):
  assert pin(b/f'joint04/all{f}.hex').read_bytes()==pin(BASE/f'probes/nes-joint266/test03/all{f}.hex').read_bytes()
  e=[r for r in ev if r[0]=='arm267' and int(r[1])==f]
  count=collections.Counter();wire=collections.Counter()
  for r in e:count[f'{int(r[2]):02x}']+=1;wire[f'{int(r[2]):02x}']+=int(r[3])
  assert sum(wire.values())==arm[f]['SPI_bytes']
  source=int(src[f]['total'])*45.454/1e6
  cumulative=int(src[f]['wirebytes_cumulative']);source_wire=cumulative-previous_wire-previous_output_wire;assert source_wire>0
  previous_wire=cumulative;previous_output_wire=arm[f]['SPI_bytes']
  rows.append(dict(frame=f,source_ms=source,output_schedule_ms=done[f],diagnostic_serial_ms=source+done[f],
   ARM_instructions=arm[f]['instructions'],ARM_CPI1_ms=arm[f]['instructions']/84000,
   SPI_bytes=arm[f]['SPI_bytes'],SPI_wire_ms=arm[f]['SPI_bytes']*8/2625,
   source_SPI_bytes=source_wire,shared_SPI_bytes=source_wire+arm[f]['SPI_bytes'],shared_SPI_wire_ms=(source_wire+arm[f]['SPI_bytes'])*8/2625,
   E0_polls=count['e0'],E8_polls=count['e8'],E9_batches=count['e9'],EA_retire=count['ea'],
   plan_SPI_bytes=wire['e8']+wire['e9']+wire['ea'],ordinary_packets=consumers[f][1],DMA_bytes=consumers[f][2]))
 warm=rows[2:];paired=[]
 for f in range(905,908):
  assert timing('joint03')[f]==done[f]
  paired.append(dict(frame=f,prior265_ms=timing('compare01')[f],shared266_ms=done[f],
   shared_delta_us=(done[f]-timing('compare01')[f])*1000,qualified_window_ms=timing('window01')[f],
   window_added_ms=timing('window01')[f]-done[f]))
 area={};hierarchy={};warnings={}
 for name in ['board26501','board02']:
  summary=res[name]['summary'];assert 'Lite Edition' in summary
  area[name]={k:int(re.search(pattern+r'\s*:\s*([\d,]+)',summary).group(1).replace(',','')) for k,pattern in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
  warnings[name]=dict(collections.Counter(re.findall(r'Warning \((\d+)\)',pin(b/name/'map.log').read_text(errors='replace'))))
  assert not res[name]['undriven_outputs']
  hierarchy[name]={}
  for line in pin(b/name/'output_files/board.map.rpt').read_text(errors='replace').splitlines():
   fields=[v.strip() for v in line.split(';')]
   if len(fields)>10 and fields[1] in ['|nes_joint267_board:native_joint267|','|nes_output260:flow|','|nes_joint257:core|','|nes_plan_path267:retained_plan267|','|nes_plan_spi200:endpoint|','|nes_plan_batch206:transport|','|nes_source_tile192:source|']:
    hierarchy[name][fields[1]]={k:int(re.match(r'\d+',v).group()) for k,v in zip(['comb','FF','RAM_bits'],fields[2:5])}
 warnings['prior240']=dict(collections.Counter(re.findall(r'Warning \((\d+)\)',pin(BASE/'probes/nes-source240/board01/map240.log').read_text(errors='replace'))))
 prior240=dict(LE=19809,comb=14966,FF=8577,RAM_bits=311904)
 current=area['board02'];prior=area['board26501'];assert current['comb']>15408
 rom=[list(map(int,r[1:])) for r in ev if r[0]=='rom267'];assert len(rom)==71
 with (out/'costs.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 r=dict(passed=True,stage='NES267',frames=71,source_bytes=old['source_bytes'],map_ranges=2069,
  actual65816_commands=522,actual65816_output_bytes=128041,actual65816_PPU_DMA_bytes=sum(x['dma_bytes'] for x in cpurows),
  actual65816_command_costs=command_costs,ordinary_packets=sum(x['ordinary_packets'] for x in rows),
  actual_ROM_tile_bytes=sum(x[1] for x in rom),DMA_bytes=sum(x['DMA_bytes'] for x in rows),max_queue_credit=4,
  source_and_metadata_exact266=True,paired=paired,warm_max_output=max(warm,key=lambda x:x['output_schedule_ms']),
  warm_max_serial=max(warm,key=lambda x:x['diagnostic_serial_ms']),warm_over_serial=sum(x['diagnostic_serial_ms']>1000/60 for x in warm),
  warm_max_shared_SPI=max(warm,key=lambda x:x['shared_SPI_bytes']),warm_wire_over=[x for x in warm if x['shared_SPI_wire_ms']>1000/60],
  warm_over_output=sum(x['output_schedule_ms']>1000/60 for x in warm),
  ARM=dict(stack_observed=res['joint04']['ARM']['stack_observed'],text=3104,bss=604,CPI=1,IRQ_cases=len(res['joint04']['ARM']['IRQ_cases']),loaded_segments=loaded_ARM,
   instructions=sum(x['ARM_instructions'] for x in rows),SPI_bytes=sum(x['SPI_bytes'] for x in rows),
   source_SPI_bytes=sum(x['source_SPI_bytes'] for x in rows),shared_SPI_bytes=sum(x['shared_SPI_bytes'] for x in rows),
   plan_SPI_bytes=sum(x['plan_SPI_bytes'] for x in rows),E0_polls=sum(x['E0_polls'] for x in rows),E8_polls=sum(x['E8_polls'] for x in rows),
   full_RUN=False,hardware_cycles=False,IRQ_preemption=False,IRQ_entry_exit_cycles=None),
  MAP=dict(prior240=prior240,prior265=prior,replacement266=current,delta_shared={k:current[k]-prior[k] for k in current},
   delta_vs240={k:current[k]-prior240[k] for k in current},comb_capacity=15408,comb_over_capacity=current['comb']-15408,
   hierarchy=hierarchy,warning_counts=warnings,removed=res['board02']['removed_instances'],retained=res['board02']['retained_instances'],
   functional_board_glue_verified=False,FIT=False,STA=False),
  full_path_ms=None,P2_selected=False,physical60fps=False,
  limitations=['ARM instruction CPI1 sensitivity; IRQ bodies at service boundaries, no NVIC preemption/entry/exit or hardware wait states',
   'Actual C planner output is input fixture; full ARM RUN/input planner/IRQ stack margin not linked',
   'Actual65816 ordinary-command bus trace replay, forced blank; map/tile consumer and final display ACK remain native model',
   'ROM physical reader and priority arbiter are actual RTL; core requests and qualified slot timing are synthetic stress policies',
   'Always-qualified 71-frame schedule is optimistic; three-frame restricted-window case is not a live NES workload or universal WCET',
   'Whole-board MAP glue resource integration unplaced and not functionally board-qualified; no FIT/STA/CDC/IO',
   'Prior266 38 negative guards retained as prior evidence; new combined ARM/ROM abort/STOP faults not qualified',
   'No active-display CGRAM/OAM/VBlank schedule or full rendered-frame oracle; source plus output is diagnostic serialized schedule'],
  artifact_hashes=pins)
 if a.contention:
  obs=read(b/a.contention/'result.json');assert obs['passed'] and obs['frames']==1 and obs['ROM_window']==1
  assert obs['rtl_hashes']==res['window01']['rtl_hashes']
  for f,h in obs['rtl_hashes'].items():assert sha(pin(b/a.contention/f))==h
  ev2=events(a.contention);waits=[list(map(int,e[1:])) for e in ev2 if e[0]=='romwait267'];assert len(waits)==1 and waits[0][3]>0
  assert timing(a.contention)[905]==timing('window01')[905]
  pin(b/a.contention/'joint266_tb.sv');pin(b/a.contention/'vsim.log')
  r['ROM_contention_observer']=dict(run=a.contention,frame=905,upstream_tile_wait_cycles=waits[0][1],unqualified_wait_cycles=waits[0][2],
   core_priority_blocks=waits[0][3],same_RTL_and_completion_time=True,
   legacy_denied_counter='ready-gated cache output; zero does not mean no contention')
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({k:r[k] for k in ['passed','frames','paired','warm_max_serial','warm_over_serial','ARM']},indent=2))


if __name__=='__main__':main()
