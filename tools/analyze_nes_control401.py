# SPDX-License-Identifier: MIT
"""Audit401 scope and measured CPU service binding; target failures stay failures."""
import argparse,collections,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_joint400 import image,timing
from analyze_nes_scope401 import ledger

def main():
 p=argparse.ArgumentParser();p.add_argument('--live',default='live02');p.add_argument('--out',type=Path,default=ROOT/'analysis/control401-verification.json');a=p.parse_args();d=BASE/'probes/nes-control401';prior=BASE/'probes/nes-joint400';live=d/a.live;pins={}
 def pin(q):pins[q.relative_to(BASE).as_posix()]=sha(q);return sha(q)
 def read(q):pin(q);return q.read_text(encoding='utf-8-sig')
 def js(q):return json.loads(read(q))
 budget=ledger(prior/'map01');assert budget==js(ROOT/'analysis/scope401-budget.json')
 ram=js(d/'ram01/result.json');assert ram['passed']and not ram['whole_MAP']and not ram['pipeline_function_verified']
 assert ram['source']==pin(d/'ram01/ram401.sv')and ram['report']==pin(d/'ram01/output_files/shape.map.rpt')
 ram_text=read(d/'ram01/output_files/shape.map.rpt')
 assert re.search(r'Simple Dual Port\s*;\s*33\s*;\s*15',ram_text)and re.search(r'Simple Dual Port\s*;\s*8\s*;\s*62',ram_text)
 baseline=js(d/'baseline400-verification.json')
 assert baseline==json.loads((ROOT/'analysis/joint400-verification.json').read_text(encoding='utf-8-sig'))
 assert baseline['live_clean']and baseline['capture917']['accepted']
 m=js(live/'manifest401.json');assert len(m['RTL'])==34 and m['test']==pin(live/'joint266_tb.sv')and not m['new_RTL']
 command=next(v for v in read(live/'vlog.log').splitlines()if v.startswith('vlog -sv '))
 assert set(command.split()[2:])==set(m['RTL'])|{'joint266_tb.sv'}
 for n,h in m['RTL'].items():assert pin(live/n)==h==pin(prior/'map01'/n)
 assert m['program']==pin(live/'program398.hex')==pin(prior/'build07/program398.hex')
 assert image(live/'output.elf')==image(prior/'build07/output.elf');pin(live/'output.elf');pin(prior/'build07/output.elf')
 assert pin(live/'executed-worker367.py')==pin(prior/'live04/executed-worker367.py')
 tb=read(live/'joint266_tb.sv');assert 'MASTER_PERIOD_PS378=46561,SNES_PHASE378=0'in tb and 'while(romcycle267<5371247)'in tb
 assert 'task rd400'in tb and 'task view401'in tb and 'poll401[0]*MASTER_NS378'in tb
 pre=js(live/'preflight398/result.json');assert pre['passed']
 native=[]
 for run,phase,count in(('native09',0,13),('native10',112,11),('native11',224,11)):
  r=js(d/run/'result.json');assert r['passed']and len(r['cases'])==count and r['WRAM']['total']==15360
  for c in r['cases']:
   q=d/run/(str(c['frame'])+('-stop'if c.get('STOP')else''));fx=js(q/'fixture401.json');hd=js(q/'hdma-result401.json')
   assert c['passed']and c['body_bytes']==1778 and fx['phase_line']==phase and not fx['production_kernel_changed']
   assert fx['kernel_SHA']==pin(q/'kernel400.sfc')==pin(prior/'native01'/str(c['frame'])/'spool.sfc')
   assert c['ROM']==pin(q/'spool.sfc')and c['events']==pin(q/'events.csv');pin(q/'timings.csv');pin(q/'hdma401.csv')
   if c['frame']>=907:
    assert hd['prior_RAM_exact']and fx['fixture_bytes']>0
    if not c.get('STOP'):assert hd['reads']>0 and hd['writes']>0
   if c.get('STOP'):assert c['PPU_jobs']==0 and not c['final_ACK']
   native.append(dict(run=run,frame=c['frame'],STOP=c.get('STOP',False),phase=phase,HDMA=hd,fixture_bytes=fx['fixture_bytes']))
 ctrl=js(d/'native08/907/hdma-result401.json');assert ctrl['fixture_end']-ctrl['fixture_begin']==44 and ctrl['reads']==ctrl['writes']==0
 service=js(d/'service02/result.json');assert service['passed']and len(service['cases'])==12
 for r in service['cases']:
  f=r['frame'];assert r==js(live/f'model401-{f}.json')==js(d/'service02'/str(f)/'model401.json')
  assert r['source_service_clocks']==sum(v['clocks']for v in r['source_jobs'])
  for n,h in r['files'].items():assert pin(live/n)==h==pin(d/'service02'/str(f)/n)
  assert r['config'][0:2]==[0,0]
  if f>=907:assert [v['phase']for v in r['samples']]==[0,112,224]and all(v['excluded_prior_setup_clocks']>0 for v in r['samples'])
 log=read(live/'vsim.log');events=list(csv.reader(read(live/'joint-events.csv').splitlines()));now=timing(events)
 old=timing(list(csv.reader(read(prior/'live04/joint-events.csv').splitlines())))
 fatal=re.findall(r'^# \*\* Fatal: (.+)$',log,re.M);clean=not fatal and 'PASS REFILL267 frames=12'in log
 rom=re.search(r'ROM368 requests=(\d+) replies=(\d+) pending=(\d+) input_requests=(\d+) input_replies=(\d+) input_pending=(\d+)',log)
 assert rom;rom_values=list(map(int,rom.groups()));assert rom_values[0]==rom_values[1]and rom_values[2]==0 and rom_values[3]==rom_values[4]and rom_values[5]==0
 finals=re.findall(r'^# FINAL398 t(\d+) f(\d+) phase(\d+) empty(\d) active(\d) tileempty(\d) sealed(\d) view(\d+) data([\da-f]+) mask([\da-f]+) written([\da-f]+) fence([\da-f]+) accepted(\d+) retired(\d+) reserved(\d)',log,re.M)
 assert all(r[2:8]==('4','1','0','1','1','12')and r[8:10]==('5a','f')and r[10]==r[11]and r[12]==r[13]and r[14]=='0'for r in finals)
 gates=[]
 for e in events:
  if e[0]!='display_gate401':continue
  f,phase,cut,tail,t=map(int,e[1:]);target={914:23,915:25}.get(f)
  row=dict(frame=f,master_phase=phase,cutoff=cut,tail_budget_clocks=tail,actual_gate_ms=t/1e9)
  if target:
   latest=(target*357368+min((cut+1)*1364-1,357368-tail))*46561/1e9
   row.update(target_VBlank=target,latest_gate_ms=latest,required_gate_advance_ms=max(0,t/1e9-latest),WCET=False)
  start=next((int(v[2])for v in events if v[:2]==['view_start401',str(f)]),None)
  end=next((int(v[2])for v in events if v[:2]==['view_end401',str(f)]),None)
  assert start is not None and end is not None
  row['view_head_service_ms']=(end-start)/1e9
  expected=next(r['head_clocks']for r in service['cases']if r['frame']==f)*46561/1e9
  extra=row['view_head_service_ms']-expected
  # Cold head ends on the last cartridge read, so rd400 still holds its
  # real200ns bus cycle and may await one host-clock response. Warm head
  # ends at a later native4212 timestamp and absorbs that handshake.
  if f<907:assert 0.000198<=extra<=0.000215
  else:assert abs(extra)<0.000002
  row['native_head_ms']=expected;row['RTL_read_completion_tail_ms']=extra
  gates.append(row)
 cap=next((v for v in now['captures']if v['frame']==917),None);mat=next((v for v in now['materialized']if v['frame']==916),None)
 stats=[]
 for line in read(live/'arm-worker.log').splitlines():
  if line.startswith('{'):
   v=json.loads(line)
   if 'frame'in v:stats.append({k:v[k]for k in('frame','instructions','SPI_bytes','source_instructions367','last_RTL_ns','prefetch_completions400')})
 ports=list(csv.reader(read(live/'ports401.csv').splitlines()));counts={key:[dict(frame=int(r[1]),counter=int(r[2]),clocks=int(r[3]))for r in ports if r[0]==key]for key in('host_count','NES_count')}
 demand=[dict(counter=int(i),clocks=int(n))for i,n in re.findall(r'^# PORT401 demand(\d+)=(\d+)',log,re.M)]
 closure=budget['control_closure'];kept=budget['kept_read_hint_mailbox']
 report=dict(audit_passed=True,scope=__doc__,selected=dict(live=a.live,native=['native09','native10','native11'],control='native08',service='service02',inherited_whole_Lite='400/map01'),implementation=dict(new_RTL=False,new_MAP=False,production_kernel_changed=False,source_plan_SPI_generic_removed=False,host_words=1979),whole=budget['whole'],control=dict(old_self_comb=3465,old_self_over=2293,closure_comb=closure['comb'],closure_FF=closure['FF'],closure_over=2343,kept_comb=kept['comb'],remaining_replacement_comb_cap=803),native_cases=native,SNES_service=dict(phases=[0,112,224],view='exact12 CPU indexed reads and head loop offsets',HDMA='previous active bank native arbitration already included in CPU event intervals',inter_job_gap_included=True,prior_fixture_time_excluded=True,original_REP_clocks_retained=44,mixed_observed_envelope=True,all_phase_WCET=False,full_resident=False),timing=now,baseline400_timing=old,exact_final_ACK_frames=[int(r[1])for r in finals],display_gates=gates,capture917=cap,capture917_margin_ms=(cap['ms']-mat['ms'])if cap and mat else None,ARM_stats=stats,ports=counts,hypothetical_merged_port_demand=demand,live_clean=clean,live_fatals=fatal,area_goal=False,FIT=False,STA=False,hardware_ready=False,physical60fps=False,pins=pins)
 report['time_goal']=bool(clean and cap and cap['accepted']and not now['presentation_gaps'])
 report['ROM_transactions']=dict(zip(('requests','replies','pending','input_requests','input_replies','input_pending'),rom_values))
 intervals=[b['ms']-x['ms']for x,b in zip(now['present'],now['present'][1:])if x['frame']>=907]
 report['max_warm_completion_interval_ms']=max(intervals)if intervals else None
 report['port_counter_names']=dict(host=['clocks','read_event','staging_read_end','read_pending','core_read_grant','core_write_grant','core_wait','header_grant','header_wait','stage_atomic','copy_write','stage_write','binding','prefill_commit','consume','IO122','queue_retire','consume_record','queue_IRQ','handler','memory_valid','IO_valid','footer_request','IO_OPEN','finish_pending','word_wait','core_during_atomic','header_during_atomic','capture_while_read_pending','IO_TAKE','unused30','unused31'],NES=['clocks','source_write','source_query','source_stall','plan_query','plan_capture','source_and_plan_query','source_capture','tile_stall','qualify','ROM_grant','hint_ROM_grant','plan_ROM_grant','core_ROM_request','hint_metaactive','unused15'])
 report['RAM_shape_check']=dict(component_MAP=True,whole_MAP=False,logical_bits=991,previous_shape=[33,15],rank_shape=[8,62],mode='Simple Dual Port',nominal_capture_M9K_budget=3,pipeline_function_verified=False,whole_physical_packing=False,palette_FF_retained=384)
 fills=[int(v[2])/1e9 for v in events if v[:2]==['hint_fill367','908']]
 if fills:
  close=baseline['hint908_window']['close_ms'];report['hint908_window']=dict(fill_ms=min(fills),close_ms=close,headroom_ms=close-min(fills),baseline400_fill_ms=baseline['hint908_window']['fill_ms'])
 report['view_native_breakdown']=[]
 for f in(907,908,914,915,916):
  model=next(r for r in service['cases']if r['frame']==f);run={0:'native09',112:'native10',224:'native11'}[model['head_phase']]
  ev=[list(map(int,r))for r in csv.reader(read(d/run/str(f)/'events.csv').splitlines())]
  views=[r[4]for r in ev if r[1]==0 and 0x6070<=r[2]<=0x607b]
  first_poll=next(r[4]for r in ev if r[1:3]==[0,0x4212]and r[4]>views[-1]);receipt=max(r[4]for r in ev if r[1:4]==[1,0x6050,0xa5])
  report['view_native_breakdown'].append(dict(frame=f,phase=model['head_phase'],receipt_to_first_view_ms=(views[0]-receipt)*46561/1e9,indexed_first_to_last_ms=(views[-1]-views[0])*46561/1e9,last_view_to_first_poll_ms=(first_poll-views[-1])*46561/1e9))
 report['same_initial_ROM_origins']=[]
 for f in(907,908):
  x=next((v for v in now['starts']if v['frame']==f),None);y=next(v for v in old['starts']if v['frame']==f)
  report['same_initial_ROM_origins'].append(dict(frame=f,same=x==y,new=x,old=y))
 if(live/'arm-result.json').exists():
  arm=js(live/'arm-result.json');report['ARM_summary']=dict(passed=arm['passed'],frames=len(arm['frames']),instructions=sum(v['instructions']for v in arm['frames']),SPI_bytes=sum(v['SPI_bytes']for v in arm['frames']),stack=arm['stack_observed'],full_RUN=arm['full_RUN'],hardware_cycles=arm['hardware_cycles'])
 for q in sorted((ROOT/'tools').glob('*401*.py')):pin(q)
 a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',newline='\n');print(json.dumps({k:report[k]for k in('audit_passed','live_clean','live_fatals','capture917','capture917_margin_ms','time_goal','area_goal')},ensure_ascii=False))
if __name__=='__main__':main()
