# SPDX-License-Identifier: MIT
"""Audit matching 398 implementation, safety tests and whole costs.
An audit PASS verifies the reported outcome; it is not a 60fps/board approval.
"""
import argparse,collections,csv,hashlib,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import crc,ELFFile

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--evidence',type=Path,default=BASE/'probes/nes-joint398')
 for name,default in dict(live='live11',unit='host10',map='map15',build='build16',hint='hint07',repeat='repeat02',repeat32='repeat03').items():p.add_argument('--'+name,default=default)
 p.add_argument('--exec',dest='execution',default='exec07')
 p.add_argument('--out',type=Path,default=ROOT/'analysis/joint398-verification.json')
 a=p.parse_args();d=a.evidence.resolve();pins={}
 def pin(q):pins[q.relative_to(BASE).as_posix()]=sha(q);return sha(q)
 def read(q):pin(q);return q.read_text(encoding='utf-8-sig')
 def js(q):return json.loads(read(q))
 def whole(q):
  r=js(q/'result.json');assert r['passed']and not r['undriven']and not r['FIT']and not r['STA']
  return {k:int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',r['summary'])[1].replace(',',''))for k,label in dict(LE='Total logic elements',comb='Total combinational functions',FF='Dedicated logic registers',RAM_bits='Total memory bits').items()}
 def cost(q):
  out={};program=[]
  for line in read(q/'output_files/board.map.rpt').splitlines():
   c=[x.strip()for x in line.split(';')]
   if len(c)>4 and re.fullmatch(r'\|[^|]+\|',c[1])and re.fullmatch(r'\d+ \(\d+\)',c[2]):
    out[c[1].strip('|')]=int(re.search(r'\((\d+)\)',c[2])[1])
    if c[1]=='|altsyncram:program398_rtl_0|':program.append(int(c[2].split()[0]))
  assert len(program)==1
  return out,program[0]
 base=js(ROOT/'analysis/joint396-verification.json');assert base['audit_passed']
 old=whole(BASE/'probes/nes-joint396/map03');now=whole(d/a.map);ea=whole(d/'map13');selfcost,programdecode=cost(d/a.map)
 pool=dict(host_and_byte_core=selfcost['nes_output260:flow']+selfcost['nes_byte398:control'],NES_source_plan_hint=sum(selfcost[n]for n in('nes_transport257:transport','nes_plan_batch206:transport','nes_plan_spi200:endpoint','nes_walk396:execution','nes_hint361:hint')),SPI=selfcost['nes_spi270:spi_front270'],queue=selfcost['nes_queue260:queue'],tile=selfcost['nes_tile_link394:tile_link'],program_decode=programdecode)
 control=sum(pool.values());retained=sum(selfcost[n]for n in('nes_core257:encoder','nes_validator278:validator'));outside=now['comb']-control-retained
 assert outside>0 and sum(pool.values())+retained+outside==now['comb']
 unit=js(d/a.unit/'result.json');assert unit['passed']and unit['frames']==12 and unit['actual_read_events']==unit['source_bytes']==25462 and unit['max_credit']==2 and len(unit['guards'])==20
 assert next(x for x in unit['guards']if x['case']==11)['checker']==2 and next(x for x in unit['guards']if x['case']==13)['checker']==3
 assert 'context port wrapped into tile/stamps'in read(d/a.unit/'record_tb.sv')and 'case=20'in read(d/a.unit/'guard20.log')
 repeat=js(d/a.repeat/'result.json');assert repeat['passed']and repeat['actual_read_events']==repeat['source_bytes']==26560 and repeat['max_credit']==2
 repeat32=js(d/a.repeat32/'result.json');assert repeat32['passed']and repeat32['actual_read_events']==repeat32['source_bytes']==26560 and repeat32['max_credit']==2
 assert read(d/a.repeat/'data905.hex')==read(d/a.repeat32/'data905.hex')
 for name,mode in((a.repeat,2),(a.repeat32,3)):
  desc=bytes(int(x,16)for x in read(d/name/'desc905.hex').split());records=[desc[i:i+12]for i in range(0,len(desc),17)]
  assert any(r[9]==5 and int.from_bytes(r[4:6],'little')==1100 and not r[6]&64 and (r[6]>>2)&3==mode for r in records)
 ex=js(d/a.execution/'result.json');assert ex['passed']and ex['vectors']==24000
 hint=js(d/a.hint/'result.json');assert hint['passed']and hint['valid_counts']==list(range(1,8))and hint['negatives']==9 and hint['EA7_generations']==[0,1,12,13,65530]and hint['STOP_freeze_clocks']==256
 assert hint['active_hint_STOP_late_DONE']and hint['late_DONE_clocks']==32
 preflight=js(d/a.live/'preflight398/result.json');assert preflight['passed']and preflight['E9_512B_16plans']and preflight['EA7_generations']==hint['EA7_generations']
 prog=js(d/a.build/'program398.json');assert ex['host_words']==prog['words']<4096
 programhash=pin(d/a.build/'program398.hex')
 for q in(d/a.map,d/a.unit,d/a.repeat,d/a.repeat32,d/a.execution,d/a.hint,d/a.live,d/a.live/'preflight398'):assert pin(q/'program398.hex')==programhash
 manifest=js(d/a.live/'manifest398.json');assert manifest['program']==programhash and manifest['ELF']==pin(d/a.live/'output.elf')
 buildELF=pin(d/a.build/'output.elf')
 def arm_image(q):
  with q.open('rb')as f:
   e=ELFFile(f)
   segments=[dict(vaddr=s['p_vaddr'],paddr=s['p_paddr'],memsz=s['p_memsz'],flags=s['p_flags'],sha256=hashlib.sha256(s.data()).hexdigest())for s in e.iter_segments()if s['p_type']=='PT_LOAD']
   symbols={s.name:int(s['st_value'])for s in e.get_section_by_name('.symtab').iter_symbols()if s.name and s['st_info']['type']!='STT_FILE'}
  return segments,symbols
 # GCC's temporary assembler FILE symbol can change the raw ELF hash. Match
 # every loaded byte and all named symbol addresses, retaining both raw ELFs.
 buildImage,buildSymbols=arm_image(d/a.build/'output.elf');liveImage,liveSymbols=arm_image(d/a.live/'output.elf')
 assert buildImage==liveImage and buildSymbols==liveSymbols
 ARMsource={}
 for q in sorted((d/a.build).iterdir()):
  if q.is_file()and q.suffix in('.c','.h','.inc','.s','.ld','.a'):
   assert pin(q)==pin(d/a.live/q.name);ARMsource[q.name]=sha(q)
 for n in('build368.log','size368.log','disassembly368.log'):pin(d/a.build/n);pin(d/a.live/n)
 assert manifest['test']==pin(d/a.live/'joint266_tb.sv');matching={}
 for n,h in manifest['RTL'].items():assert pin(d/a.live/n)==h==pin(d/a.map/n);matching[n]=h
 assert len(matching)==33
 separated_manifest=js(d/'ea01/manifest396.json')
 for n,h in separated_manifest['RTL'].items():assert pin(d/'ea01'/n)==h==pin(d/'map13'/n)
 assert len(separated_manifest['RTL'])==32
 for n,h in unit['RTL'].items():assert pin(d/a.unit/n)==h==pin(d/a.map/n)
 for test in(hint,preflight):
  for n,h in test['pins'].items():
   if n.endswith('.sv')and n!='hint398_tb.sv':assert h==pin(d/a.map/n)
 assert ex['pins']['nes_byte398.sv']==pin(d/a.map/'nes_byte398.sv')
 frontier=js(d/'armguard02/result.json');assert frontier['passed']and frontier['cases']==1770 and frontier['full_cases']==450 and frontier['ELF']==buildELF
 owner=js(d/'owner04/result.json');assert owner['passed']and len(owner['cases'])==3 and owner['ELF']==buildELF
 oldowner=js(d/'owner05/cases.json');assert oldowner[0]['packet_count']>1
 ARM71=js(d/'arm02/result.json');assert ARM71['passed']and len(ARM71['cases'])==71 and all(r['coverage_exact']for r in ARM71['cases'])and ARM71['ELF']==buildELF
 size=list(map(int,read(d/a.build/'size368.log').splitlines()[1].split()[:3]));assert size==[35780,4,48728]
 # Preserved signature and port gates; never reclassify these as removed logic.
 host=read(d/a.live/'nes_mux260.sv');queue=read(d/a.live/'nes_queue260.sv');spi=read(d/a.live/'nes_spi270.sv');tile=read(d/a.live/'nes_tile_link394.sv')
 assert 'nes_check396 record_check'not in host and 'case(state)'not in host
 assert 'ma<224'in host and 'if(mv&&ma>=224)failed<=1'in host
 assert 'reserved398<=1'in queue and 'storage_empty312=empty315&&!reserved398'in queue
 assert 'memory[0:1023]'in tile and 'hint_metaactive398' in tile
 assert 'hint_count_ok398&&count==hint_length398-1'in spi and 'last signature byte' in spi
 assert not re.search(r'149:crc_good280<=output_status|150:tail_good280<=output_status',spi)
 live=d/a.live;log=read(live/'vsim.log');tb=read(live/'joint266_tb.sv');assert 'MASTER_PERIOD_PS378=46561,SNES_PHASE378=0'in tb and 'while(romcycle267<5371247)'in tb and '-gROM_WINDOW=1'in log
 events=list(csv.reader(read(live/'joint-events.csv').splitlines()))
 def timing(rows):
  present=[dict(frame=int(r[1]),ms=int(r[2])/1e9,VBlank=int(r[3]),phase=int(r[4]))for r in rows if r[0]=='present394']
  done=[dict(frame=int(r[1]),ms=int(r[2])/1e9)for r in rows if r[0]=='frame_done']
  capture=[dict(frame=int(r[1]),owned=bool(int(r[2])),accepted=bool(int(r[3])),ms=int(r[-1])/1e9)for r in rows if r[0]=='capture_attempt367']
  starts=[dict(frame=int(r[1]),ms=int(r[2])/1e9,ROM_cycle=int(r[3]))for r in rows if r[0]=='start319']
  materialized=[dict(frame=int(r[1]),ROM_cycle=int(r[2]),ms=int(r[3])/1e9)for r in rows if r[0]=='materialized366']
  gaps=[dict(after_frame=x['frame'],before_frame=y['frame'],VBlanks=y['VBlank']-x['VBlank'])for x,y in zip(present,present[1:])if x['frame']>=907 and y['VBlank']!=x['VBlank']+1]
  return dict(present=present,done=done,captures=capture,starts=starts,materialized=materialized,presentation_gaps=gaps,first_missed_capture=next((r['frame']for r in capture if not r['accepted']),None))
 timed=timing(events);separated=timing(list(csv.reader(read(d/'ea01/joint-events.csv').splitlines())))
 assert next(r for r in separated['present']if r['frame']==908)['VBlank']==17 and next(r for r in separated['captures']if r['frame']==911)['accepted']and separated['first_missed_capture']==917
 q908=next((r for r in timed['present']if r['frame']==908),None);c911=next((r for r in timed['captures']if r['frame']==911),None);done906=next((r for r in timed['done']if r['frame']==906),None)
 failures=re.findall(r'^# \*\* Fatal: (.+)$',log,re.M);clean=not failures and 'PASS REFILL267 frames=12'in log
 finals=re.findall(r'^# FINAL398 t(\d+) f(\d+) phase(\d+) empty(\d) active(\d) tileempty(\d) sealed(\d) view(\d+) data([\da-f]+) mask([\da-f]+) written([\da-f]+) fence([\da-f]+) accepted(\d+) retired(\d+) reserved(\d)',log,re.M)
 assert sorted(int(r[1])for r in finals)==list(range(905,917))
 assert all(r[2:8]==('4','1','0','1','1','12')and r[8:10]==('5a','f')and r[10]==r[11]and r[12]==r[13]and r[14]=='0'for r in finals)
 assert failures==['capture coverage367'],'unexpected additional failure; review before reporting capture-only rejection'
 ROMcounts=re.search(r'ROM368 requests=(\d+) replies=(\d+) pending=(\d+) input_requests=(\d+) input_replies=(\d+) input_pending=(\d+)',log)
 assert ROMcounts and ROMcounts[1]==ROMcounts[2]and ROMcounts[3]=='0'and ROMcounts[4]==ROMcounts[5]and ROMcounts[6]=='0'
 warmframes=[r for r in timed['present']if r['frame']>=907];sequential=all(b['VBlank']==a['VBlank']+1 for a,b in zip(warmframes,warmframes[1:]))
 timegoal=bool(clean and q908 and q908['VBlank']==17 and c911 and c911['accepted']and not timed['first_missed_capture']and sequential)
 ea_packets=[];ARMrows=[]
 worker={}
 for line in read(live/'arm-worker.log').splitlines():
  if line.startswith('{'):
   obj=json.loads(line)
   if 'frame'in obj:worker[obj['frame']]=obj
 for q in sorted(live.glob('arm[0-9][0-9][0-9].json')):
  obj=js(q);frame=int(q.stem[3:]);transfers=obj['transfers'];source_bytes=0
  for tr in transfers:
   w=bytes.fromhex(tr['tx'])
   if w and w[0]in(0,0xd4):source_bytes+=len(w)
  output_events=[r for r in events if r[:2]==['ARM_wire_start334',str(frame)]];output_bytes=sum(int(r[3])for r in output_events)
  if frame in worker:
   stat=worker[frame];assert stat['SPI_bytes']==source_bytes+output_bytes
   ARMrows.append(dict(frame=frame,instructions_reported=stat['instructions'],source_instructions_reported=stat['source_instructions367'],instruction_reports_not_added=True,SPI_bytes=stat['SPI_bytes'],source_read_wire_bytes=source_bytes,output_and_commit_wire_bytes=output_bytes,output_and_commit_commands=dict(collections.Counter(f'{int(r[2]):02x}'for r in output_events)),source_D4_commands=sum(bool(tr['tx'])and tr['tx'].startswith('d4')for tr in transfers),logged_SPI_IRQ_instructions=sum(tr.get('IRQ_instructions',0)for tr in transfers),logged_SPI_exception_cycles=sum(tr.get('exception_cycles284',0)for tr in transfers),IRQ_log_is_precommit_subset=True,wire_only_ms=stat['SPI_bytes']*8/2.625e6*1000,wire_is_already_in_actual_schedule=True))
  emitted=[bytes.fromhex(tr['tx'])for tr in transfers if tr['tx'].startswith('e1')]
  assert emitted and emitted[-1][1]==0xa3 and sum(w[1]==0xa3 for w in emitted)==1,'E1 record after END or missing END'
  for tr in obj['transfers']:
   w=bytes.fromhex(tr['tx'])
   if w and w[0]==0xea and len(w)>7:
    n=w[1];assert 1<=n<=7 and len(w)==14+2*n and int.from_bytes(w[-2:],'little')==crc(w[:-2])
    tags=[int.from_bytes(w[i:i+2],'little')for i in range(12,len(w)-2,2)];assert len(set(tags))==n and all(t<8192 for t in tags)
    ea_packets.append(dict(frame=frame,tags=tags,bytes=len(w)))
 oldevents=list(csv.reader(read(BASE/'probes/nes-joint396/live07/joint-events.csv').splitlines()));oldtimed=timing(oldevents);start_compare=[]
 for f in(907,908):
  b=next((r for r in oldtimed['starts']if r['frame']==f),None);n=next((r for r in timed['starts']if r['frame']==f),None)
  if b and n:start_compare.append(dict(frame=f,baseline_ms=b['ms'],actual_ms=n['ms'],baseline_ROM_cycle=b['ROM_cycle'],actual_ROM_cycle=n['ROM_cycle'],actual_delta_ms=n['ms']-b['ms'],late_starts_are_charged_not_phase_reset=True))
 hint_events=[dict(event=r[0],ms=int(r[-1])/1e9)for r in events if len(r)>2 and r[1]=='908'and r[0]in('hint_start367','hint_end367','hint_fill367')]
 firstfill=next((r['ms']for r in hint_events if r['event']=='hint_fill367'),None)
 EAfill=next(float(r[-1])/1e9 for r in csv.reader(read(d/'ea01/joint-events.csv').splitlines())if r[:2]==['hint_fill367','908'])
 area_goal=control<=1172 and now['comb']<=15253
 # Native service is measured CPU bus replay, not a new lockstep CPU proof.
 native=BASE/'probes/nes-jobs394/native04/905/spool.sfc';image=native.read_bytes();pin(native)
 assert bytes(int(x,16)for x in read(d/a.map/'sink-program.hex').split())==image[:0xfc0]+image[0x7fc0:0x8000]
 for q in(ROOT/'tools').glob('*398.py'):pin(q)
 for q in(ROOT/'src/fpga/nes_exec398').iterdir():
  if q.is_file():pin(q)
 report=dict(audit_passed=True,production_selected=False,time_goal_met=timegoal,area_goal_met=area_goal,FIT=False,STA=False,scope=__doc__,selected=dict(build=a.build,whole_map=a.map,live=a.live,unit=a.unit,hint=a.hint,execution=a.execution,repeat=a.repeat),whole=dict(baseline396=old,EA_only398=ea,joint398=now,delta_vs396={k:now[k]-old[k]for k in old}),control=dict(baseline=4027,pool=pool,total=control,cap=1172,over_cap=control-1172,retained=retained,outside=outside,net_control_deletion=4027-control,device_comb_deficit=now['comb']-15408,with155reserve_deficit=now['comb']-15253,host_plus_program_alone=pool['host_and_byte_core']+programdecode),program=dict(code_words=prog['words'],allocated_words=4096,bits=18,context_RAM_bytes=1024,context_range=[800,1023],tag_range=[928,941]),guards=dict(independent_vectors=24000,physical_errors_STOP=len(unit['guards']),actual_reads=unit['actual_read_events'],repeat_reads=repeat['actual_read_events'],max_credit=2,EA_valid_counts=hint['valid_counts'],EA7_generations=hint['EA7_generations'],EA_negatives=9,E9_512B=preflight['E9_512B_16plans'],frontier_cases=1770),ARM=dict(text=size[0],data=size[1],BSS=size[2],ELF=manifest['ELF'],EA_packets=ea_packets,CPI=1,hardware_WCET=False),timing=dict(actual=timed,separated_EA_only=separated,actual_runtime_clean=clean,fatal_messages=failures,VBlank908=q908['VBlank']if q908 else None,capture911=bool(c911 and c911['accepted']),startup907_recovered=bool(done906 and done906['ms']<5371247*46561/1e9),cold906_done=done906,same_initial_capture_and_ROM_phase=True,consecutive_present_VBlanks=sequential,full_native_CPU_lockstep=False),remaining_bodies=['source writer/D4 deadline checks','NES plan decode','SPI response snapshot','hot read/token/publication IO'],matching_whole_functional_RTL=matching,physical60fps=False,open=['1172 control budget','remaining body replacement','FIT/STA','full resident/ARM WCET','71heavy/multipleROMphase','normal STOP recovery','MMC4/MMC5'],pins=pins)
 report['ARM']['schedule_rows']=ARMrows
 comparisons=[]
 refs={}
 for name,path in(('baseline396',BASE/'probes/nes-joint396/live07'),('EA_only398',d/'ea01')):
  refs[name]={r['frame']:r for r in(json.loads(line)for line in read(path/'arm-worker.log').splitlines()if line.startswith('{'))if 'frame'in r}
 for r in ARMrows:
  compare=dict(frame=r['frame'],joint_SPI_bytes=r['SPI_bytes'],joint_instructions=r['instructions_reported'])
  for name,rows in refs.items():
   if r['frame']in rows:
    ref=rows[r['frame']];compare[name]=dict(SPI_bytes=ref['SPI_bytes'],instructions=ref['instructions'],SPI_byte_delta=r['SPI_bytes']-ref['SPI_bytes'],instruction_delta=r['instructions_reported']-ref['instructions'])
  comparisons.append(compare)
 report['ARM']['schedule_comparison']=comparisons
 report['ARM']['component_ELF']=buildELF
 report['ARM']['component_live_PT_LOAD_and_symbols_exact']=True
 report['ARM']['PT_LOAD']=liveImage
 report['ARM']['matching_materialized_sources']=ARMsource
 report['timing']['observed_start_comparison']=start_compare
 warmdone=[r for r in timed['done']if r['frame']>=907]
 intervals=[dict(after_frame=x['frame'],before_frame=y['frame'],ms=y['ms']-x['ms'])for x,y in zip(warmdone,warmdone[1:])]
 report['timing']['completion_intervals']=intervals
 report['timing']['max_warm_completion_interval_ms']=max((r['ms']for r in intervals),default=None)
 report['timing']['completed_frames_with_exact_final_ACK']=12
 report['timing']['all_final_ACK_gates_passed']=True
 report['timing']['only_capture_coverage_assertion_failed']=True
 report['timing']['ROM_pairs']=int(ROMcounts[1]);report['timing']['input_origin_ROM_pairs']=int(ROMcounts[4]);report['timing']['ROM_pending']=0
 report['timing']['hint908_events']=hint_events
 report['timing']['hint908_ROM_window']=dict(close_ms=282.742976208,actual_fill_ms=firstfill,margin_ms=282.742976208-firstfill if firstfill else None,EA_only_fill_ms=EAfill,joint_extra_vs_EA_only_ms=firstfill-EAfill if firstfill else None,wire_only_saved_ms=8*8/2.625e6*1000,return_markers_are_not_SS_edges=True)
 firstmiss=next((r for r in timed['captures']if not r['accepted']),None)
 if firstmiss:
  predecessor=firstmiss['frame']-1
  s=next((r for r in timed['starts']if r['frame']==predecessor),None);m=next((r for r in timed['materialized']if r['frame']==predecessor),None)
  report['timing']['next_capture_ownership_debt']=dict(missed_frame=firstmiss['frame'],deadline_ms=firstmiss['ms'],predecessor=predecessor,source_start_ms=s['ms']if s else None,materialized_ms=m['ms']if m else None,start_after_deadline_ms=s['ms']-firstmiss['ms']if s else None,materialized_after_deadline_ms=m['ms']-firstmiss['ms']if m else None,not_a_full_60fps_time_bound=True)
 report['guards']['repeat32_reads']=repeat32['actual_read_events']
 report['guards']['active_hint_STOP_late_DONE']=True
 report['guards']['ARM_map_ownership_cases']=owner['cases']
 report['guards']['old_ARM_duplicate_reproduced']=True
 report['guards']['ARM_component_exact_coverage_frames']=71
 oldEND=bytes.fromhex(read(d/'live09/arm-req6482').splitlines()[1]);oldextra=bytes.fromhex(read(d/'live09/arm-req6499').splitlines()[1])
 assert oldEND[:2]==b'\xe1\xa3'and oldextra[:2]==b'\xe1\xab'and int.from_bytes(oldextra[5:9],'little')==11
 assert (oldEND[3:5],oldextra[3:5])==(bytes.fromhex('1d00'),bytes.fromhex('1e00'))
 report['guards']['old_live915_END_then_MAP']=dict(END_bytes=len(oldEND),extra_MAP_bytes=len(oldextra),END_ms=434.690911,extra_MAP_ms=435.286732,FPGA_rejection_correct=True)
 report['ARM']['no_E1_after_END_in_completed_frame_logs']=True
 report['separated_EA_only_matching_RTL']=separated_manifest['RTL']
 report['separated_EA_only_precedes_ARM_END_fix']=True
 report['selected']['ARM_component']='arm02'
 report['selected']['ARM_frontier']='armguard02'
 report['selected']['ARM_ownership']='owner04'
 report['selected']['repeat32']=a.repeat32
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',newline='\n');print(json.dumps({k:report[k]for k in('audit_passed','time_goal_met','area_goal_met','whole','control','guards')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
