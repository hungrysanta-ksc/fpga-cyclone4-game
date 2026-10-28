# SPDX-License-Identifier: MIT
"""Audit actual400 implementation and outcomes. PASS is evidence consistency,
not acceptance of a failed capture/area target or physical hardware signoff.
"""
import argparse,collections,csv,hashlib,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile
from cost_nes_joint400 import measure

def image(q):
 with q.open('rb')as f:
  e=ELFFile(f)
  segments=[(s['p_vaddr'],s['p_paddr'],s['p_memsz'],s['p_flags'],hashlib.sha256(s.data()).hexdigest())for s in e.iter_segments()if s['p_type']=='PT_LOAD']
  symbols={s.name:int(s['st_value'])for s in e.get_section_by_name('.symtab').iter_symbols()if s.name and s['st_info']['type']!='STT_FILE'}
 return segments,symbols

def timing(events):
 present=[dict(frame=int(r[1]),ms=int(r[2])/1e9,VBlank=int(r[3]))for r in events if r[0]=='present394']
 done=[dict(frame=int(r[1]),ms=int(r[2])/1e9)for r in events if r[0]=='frame_done']
 capture=[dict(frame=int(r[1]),owned=bool(int(r[2])),accepted=bool(int(r[3])),ms=int(r[-1])/1e9)for r in events if r[0]=='capture_attempt367']
 starts=[dict(frame=int(r[1]),ms=int(r[2])/1e9,ROM_cycle=int(r[3]))for r in events if r[0]=='start319']
 materialized=[dict(frame=int(r[1]),ROM_cycle=int(r[2]),ms=int(r[3])/1e9)for r in events if r[0]=='materialized366']
 gaps=[dict(after=a['frame'],before=b['frame'],VBlanks=b['VBlank']-a['VBlank'])for a,b in zip(present,present[1:])if a['frame']>=907 and b['VBlank']!=a['VBlank']+1]
 return dict(present=present,done=done,captures=capture,starts=starts,materialized=materialized,presentation_gaps=gaps,first_missed_capture=next((r['frame']for r in capture if not r['accepted']),None))

def main():
 p=argparse.ArgumentParser();p.add_argument('--live',default='live04');p.add_argument('--map',default='map01');p.add_argument('--build',default='build07');p.add_argument('--out',type=Path,default=ROOT/'analysis/joint400-verification.json');a=p.parse_args();d=BASE/'probes/nes-joint400';pins={}
 def pin(q):pins[q.relative_to(BASE).as_posix()]=sha(q);return sha(q)
 def read(q):pin(q);return q.read_text(encoding='utf-8-sig')
 def js(q):return json.loads(read(q))
 unit=js(d/'host03/result.json');assert unit['passed']and unit['frames']==12 and unit['actual_read_events']==unit['source_bytes']==25462 and unit['max_credit']==2 and len(unit['guards'])==20
 assert next(r for r in unit['guards']if r['case']==11)['checker']==2 and next(r for r in unit['guards']if r['case']==13)['checker']==3
 hint=js(d/'hint02/result.json');assert hint['passed']and hint['valid_counts']==list(range(1,8))and hint['E9_512B_16plans']and hint['EA7_generations']==[0,1,12,13,65530]and hint['active_hint_STOP_late_DONE']and hint['late_DONE_clocks']==32
 ex=js(d/'exec02/result.json');assert ex['passed']and ex['vectors']==24000 and ex['host_words']==1979
 owner=js(d/'armguard18/result.json');assert owner['passed']and owner['old_identity_preserved']and owner['STOP_before_deferred_commit']and owner['no_op_reports_no_SPI']
 frontier=js(d/'armguard16/result.json');assert frontier['passed']and frontier['cases']==1770 and frontier['full_cases']==450
 end=js(d/'armguard17/result.json');assert end['passed']and len(end['cases'])==3
 arm=js(d/'arm06/result.json');assert arm['passed']and len(arm['cases'])==71 and all(r['coverage_exact']for r in arm['cases'])
 build=d/a.build;live=d/a.live;mp=d/a.map;elf=pin(build/'output.elf')
 for r in(owner,frontier,end,arm):assert r['ELF']==elf
 assert image(build/'output.elf')==image(live/'output.elf');pin(live/'output.elf')
 for q in build.iterdir():
  if q.is_file()and q.suffix in('.c','.h','.inc','.s','.ld','.a'):assert pin(q)==pin(live/q.name)
 size=list(map(int,read(build/'size368.log').splitlines()[1].split()[:3]));assert size==[36800,4,48792]
 manifest=js(live/'manifest400.json');assert len(manifest['RTL'])==34 and manifest['test']==pin(live/'joint266_tb.sv')
 for n,h in manifest['RTL'].items():assert pin(live/n)==h==pin(mp/n)
 prog=pin(build/'program398.hex');assert prog==manifest['program']
 for q in(mp,live,d/'host03',d/'hint02',d/'exec02',live/'preflight398'):assert pin(q/'program398.hex')==prog
 for n,h in unit['RTL'].items():assert pin(mp/n)==h==pin(d/'host03'/n)
 for n,h in hint['pins'].items():
  if n.endswith('.sv')and n!='hint398_tb.sv':assert pin(mp/n)==h
 pre=js(live/'preflight398/result.json');assert pre['passed']and pre['pins']['program398.hex']==prog
 native=js(d/'native01/result.json');assert native['passed']and len(native['cases'])==13 and all(r['body_bytes']==1778 for r in native['cases'])and native['WRAM']['total']==15360
 assert pin(mp/'native396/spool.sfc')==pin(d/'native01/907/spool.sfc')
 for f in range(905,917):
  assert pin(d/'arm06'/f'wire{f}.json')==pin(BASE/'probes/nes-joint398/arm02'/f'wire{f}.json')
 cost=measure(mp);pin(mp/'output_files/board.map.rpt');baseline=js(ROOT/'analysis/joint398-verification.json')
 oldwhole={'LE':22157,'comb':17428,'FF':8916,'RAM_bits':382304}
 delta={k:cost['whole'][k]-v for k,v in oldwhole.items()}
 tb=read(live/'joint266_tb.sv');assert 'MASTER_PERIOD_PS378=46561,SNES_PHASE378=0'in tb and 'while(romcycle267<5371247)'in tb and 'task rd400'in tb
 worker=read(live/'executed-worker367.py');assert "source_prefetch_policy400"in worker and 'prefetch_completions400=word'in worker
 host=read(live/'nes_mux260.sv');assert '.irq(1\'b0)'in host and 'read_event400'in host and 'read_count==chunk_length&&ready359&&!read_pending'in host and 'ma<224'in host
 assert 'storage_empty312=empty315&&!reserved398'in read(live/'nes_queue260.sv')
 h=read(ROOT/'src/fpga/nes_joint400/hint.sv');assert '!busy&&!used'in h
 log=read(live/'vsim.log');assert '-gROM_WINDOW=1'in log
 events=list(csv.reader(read(live/'joint-events.csv').splitlines()));now=timing(events)
 old=timing(list(csv.reader(read(BASE/'probes/nes-joint398/live11/joint-events.csv').splitlines())))
 failures=re.findall(r'^# \*\* Fatal: (.+)$',log,re.M)
 ack_ms={int(f):int(t)/1e9 for t,f in re.findall(r'^# FINAL398 t(\d+) f(\d+) ',log,re.M)}
 stats=[]
 for line in read(live/'arm-worker.log').splitlines():
  if line.startswith('{'):
   r=json.loads(line)
   if 'frame'in r:
    assert 'prefetch_completions400'in r
    stats.append({k:r[k]for k in('frame','instructions','source_instructions367','SPI_bytes','last_RTL_ns','prefetch_attempts400','prefetch_completions400','prefetch_yields400')})
 received=[];wire=[]
 for q in sorted(live.glob('after-finish400-*.json')):
  processing=int(q.stem.rsplit('-',1)[1]);tr=js(q)['transfers'];prefix_ms=None
  for r in tr:
   tx=bytes.fromhex(r['tx']);rx=bytes.fromhex(r['rx'])
   if r.get('source_phase367'):
    assert r['wire_owned394']==0,'source overwrote an output-owned wire buffer'
   if r.get('source_phase367')==1:prefix_ms=r['RTL_ns']/1e6
   if r.get('source_phase367')==2 and rx[:3]==b'N5\x02':
    target=int.from_bytes(rx[12:16],'little')+904
    assert target in(processing,processing+1)
    ack=ack_ms.get(processing);next_input=target==processing+1
    tails=[e for e in events if e[0]=='source_tail367'and int(e[1])==processing and int(e[2])==len(rx)]
    tail=min(tails,key=lambda e:abs(int(e[3])-r['RTL_ns']*1000));assert abs(int(tail[3])-r['RTL_ns']*1000)<2000
    # shift367 drives 8 bits at two190.476190476ns half cycles, followed
    # by two2us SS-release waits before logging source_tail367.
    assert '#190.476190476'in tb
    first_clock=int(tail[3])/1e9-.004-len(rx)*8*2*190.476190476/1e6+190.476190476/1e6
    received.append(dict(processing_frame=processing,input_frame=target,checked_prefix_end_ms=prefix_ms,first_payload_clock_ms=first_clock,first_block_received_ms=r['RTL_ns']/1e6,old_RTL_final_ACK_ms=ack,early=next_input and ack is not None and first_clock<ack,block_received_before_old_ACK=next_input and ack is not None and r['RTL_ns']/1e6<ack))
   if tx:wire.append(dict(processing_frame=processing,command=f'{tx[0]:02x}',bytes=len(tx),RTL_ns=r['RTL_ns'],source_phase=r.get('source_phase367',0),IRQ_instructions=r.get('IRQ_instructions',0),exception_cycles=r.get('exception_cycles284',0)))
 finals=re.findall(r'^# FINAL398 t(\d+) f(\d+) phase(\d+) empty(\d) active(\d) tileempty(\d) sealed(\d) view(\d+) data([\da-f]+) mask([\da-f]+) written([\da-f]+) fence([\da-f]+) accepted(\d+) retired(\d+) reserved(\d)',log,re.M)
 assert all(r[2:8]==('4','1','0','1','1','12')and r[8:10]==('5a','f')and r[10]==r[11]and r[12]==r[13]and r[14]=='0'for r in finals)
 capture917=next((r for r in now['captures']if r['frame']==917),None)
 clean=not failures and 'PASS REFILL267 frames=12'in log
 timegoal=bool(clean and capture917 and capture917['accepted']and not now['presentation_gaps']and stats and max(r['prefetch_completions400']for r in stats)>0 and any(r['early']for r in received))
 report=dict(audit_passed=True,scope=__doc__,selected=dict(build=a.build,whole_map=a.map,live=a.live,host='host03',hint='hint02',execution='exec02',ARM='arm06',ownership='armguard18'),implementation=dict(fixed_transaction_ingress=True,read_end_single_owner=True,receive_ahead=True,deferred_semantic_commit=True,header_DMA=True,generic_semantic_interpreter_removed=False,source_plan_SPI_bodies_fully_removed=False,host_words=1979,ROM_words_charged=4096),safety=dict(host_frames=12,actual_reads=25462,guards=20,independent_duplicate_fault=2,independent_coverage_fault=3,STOP_freeze=256,hint_late_DONE=32,EA_counts=list(range(1,8)),bounds_vectors=24000,ARM71=True,old_display_identity=True,STOP_before_deferred_commit=True),ARM_size=dict(text=size[0],data=size[1],BSS=size[2],delta_vs398=dict(text=size[0]-35780,data=0,BSS=size[2]-48728),fullresident=False),whole=cost,whole_delta_vs398=delta,control_delta_vs398=cost['control']-3471,baseline398=old,timing=now,live_fatals=failures,exact_final_ACK_frames=[int(r[1])for r in finals],ARM_live_stats=stats,live_clean=clean,capture917=capture917,time_goal=timegoal,area_goal=cost['control']<=1172 and cost['whole']['comb']<=15253 and cost['whole']['LE']<=15408,FIT=False,STA=False,physical60fps=False,hardware_ready=False,pins=pins)
 report['received_input_identity']=received
 for run in('repeat01','repeat02'):
  repeat=js(d/run/'result.json');assert repeat['passed']and repeat['frames']==12 and repeat['actual_read_events']==repeat['source_bytes']==26560 and repeat['max_credit']==2
  for n,h in repeat['RTL'].items():assert pin(mp/n)==h==pin(d/run/n)
  assert pin(d/run/'program398.hex')==prog
 assert read(d/'repeat01/data905.hex')==read(d/'repeat02/data905.hex')
 report['safety']['repeat16_32_1100B']=dict(reads_each=26560,chunk_sizes=[512,512,76],max_credit=2)
 armrun=js(live/'arm-result.json');oldarm=js(BASE/'probes/nes-joint398/live11/arm-result.json')
 assert armrun['passed']and len(armrun['frames'])==12
 report['ARM_live_totals']={}
 for label,r in(('old398',oldarm),('new400',armrun)):
  report['ARM_live_totals'][label]=dict(instructions=sum(v['instructions']for v in r['frames']),SPI_bytes=sum(v['SPI_bytes']for v in r['frames']),observed_component_stack=r['stack_observed'],hardware_cycles=r['hardware_cycles'],full_RUN=r['full_RUN'])
 priorpoll=js(d/'live03/arm-result.json');priorSPI=sum(r['SPI_bytes']for r in priorpoll['frames']);assert report['ARM_live_totals']['new400']['SPI_bytes']<priorSPI
 report['polling_fix']=dict(previous_live03_SPI_bytes=priorSPI,selected_SPI_bytes=report['ARM_live_totals']['new400']['SPI_bytes'],saved_bytes=priorSPI-report['ARM_live_totals']['new400']['SPI_bytes'],no_source_SPI_keeps_plan_cache_and_WFI=True)
 report['SNES_service_scope']=dict(source_jobs_and_header_DMA='exact native component bus-event offsets',display_tail='native component bus-event offsets after the modeled VBlank gate',view12='existing400ns read tasks, not the full native indexed-loop CPU timing',previous_active_HDMA_arbitration_bound=False,resident_CPU_lockstep=False,physical_capture_headroom_proven=False)
 assert 'if(received400==2){plan_cache282=0;wait_armed284=0;}'in read(live/'nes_refill267.c')
 report['max_warm_completion_interval_ms']=max(b['ms']-a['ms']for a,b in zip(now['present'],now['present'][1:])if a['frame']>=907)
 report['matching_initial_ROM_origins']=[]
 for f in(907,908):
  old_start=next(r for r in old['starts']if r['frame']==f);new_start=next(r for r in now['starts']if r['frame']==f);assert old_start==new_start
  report['matching_initial_ROM_origins'].append(new_start)
 deadline=next(r['ms']for r in now['captures']if r['frame']==917)
 material=next(r['ms']for r in now['materialized']if r['frame']==916)
 oldmaterial=next(r['ms']for r in old['materialized']if r['frame']==916)
 report['capture917_margin']=dict(deadline_ms=deadline,materialized916_ms=material,headroom_ms=deadline-material,old_materialized916_ms=oldmaterial,improvement_ms=oldmaterial-material,scope='12-frame replay plus917 capture; not918+/sustained60fps')
 fills=[int(r[2])/1e9 for r in events if r[:2]==['hint_fill367','908']]
 close=baseline['timing']['hint908_ROM_window']['close_ms'];assert fills and min(fills)<close
 report['hint908_window']=dict(close_ms=close,fill_ms=min(fills),headroom_ms=close-min(fills),old_fill_ms=baseline['timing']['hint908_ROM_window']['actual_fill_ms'],same_start_and_ROM_cycle=True)
 report['remaining_display_advance_lower_bounds']=[]
 for f,target in((914,23),(915,25)):
  cfg=[int(x,16)for x in read(live/f'jobs394-config{f}.hex').split()]
  stored=max(int(r[4])/1e9 for r in events if r[:2]==['stored394',str(f)])
  # Last source-job completion precedes12 slow view reads and the measured
  # native pre-gate service. Omitted sealing/port/poll work only increases
  # the actual required advance. This is not a newly measured exact gate.
  minimum_gate=stored+12*400/1e6+cfg[1]*46561/1e9
  latest=(target*357368+min((cfg[4]+1)*1364-1,357368-cfg[2]))*46561/1e9
  report['remaining_display_advance_lower_bounds'].append(dict(frame=f,target_VBlank=target,last_source_job_ms=stored,minimum_gate_ms=minimum_gate,latest_gate_ms=latest,additional_advance_at_least_ms=max(0,minimum_gate-latest),exact_gate_measured=False,WCET=False))
 imagebytes=(d/'native01/905/spool.sfc').read_bytes();assert bytes(int(x,16)for x in read(mp/'sink-program.hex').split())==imagebytes[:0xfc0]+imagebytes[0x7fc0:0x8000]
 profile=js(live/'manifest394.json')
 for r in profile['profiles']:
  f=r['frame'];assert r['events']==pin(d/'native01'/str(f)/'events.csv')and r['native']==pin(d/'native01'/str(f)/'spool.sfc')
  assert r['config']==[int(x,16)for x in read(live/f'jobs394-config{f}.hex').split()]
 report['wire_summary']=dict(transactions=len(wire),bytes=sum(r['bytes']for r in wire),commands=dict(collections.Counter(r['command']for r in wire)),SPI_IRQ_instructions=sum(r['IRQ_instructions']for r in wire),SPI_exception_cycles=sum(r['exception_cycles']for r in wire),scope='Recorded transfer subset and processing-frame attribution; includes source of next frame, not added to live timeline a second time.')
 for path in sorted((ROOT/'tools').glob('*400*.py'))+sorted((ROOT/'src/fpga/nes_joint400').glob('*.sv')):pin(path)
 a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k]for k in('audit_passed','live_clean','time_goal','area_goal','live_fatals','capture917','whole','whole_delta_vs398')},ensure_ascii=False))
if __name__=='__main__':main()
