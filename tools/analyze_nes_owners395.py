# SPDX-License-Identifier: MIT
"""395 clock/port evidence and replacement admission budgets.
No new execution RTL, whole MAP, shifted-ROM prediction or60fps proof."""
import argparse,bisect,csv,hashlib,json,re
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from probe_nes_arm264 import plans,u16

def main():
 p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--out',type=Path,default=ROOT/'analysis/owners395-verification.json');a=p.parse_args();d=a.trace.resolve();pins={}
 def read(q):pins[q.relative_to(BASE).as_posix()]=sha(q);return q.read_text(encoding='utf-8-sig')
 def js(q):return json.loads(read(q))
 old=js(ROOT/'analysis/jobs394-verification.json');assert old['audit_passed']and old['whole']['candidate394']['comb']==17574 and old['whole']['remaining_with_155_reserve']==2321
 m=js(d/'manifest395.json');assert m['RTL']==old['matching_whole_functional_RTL'];assert all(sha(d/n)==h for n,h in m['RTL'].items());assert sha(d/'output.elf')==m['ELF']
 log=read(d/'vsim.log');assert 'startup missed fixed capture368'in log and 'Errors: 1, Warnings: 0'in log
 r=js(d/'result.json');assert r['audit_passed']and not r['implementation_changed'];ev=list(csv.reader(read(d/'ports395.csv').splitlines()));assert ev[-1][0]=='end';end=int(ev[-1][-1])
 rows=[]
 for f in (905,906):
  nes=[(int(x[-1]),int(x[2]))for x in ev if x[:2]==['nes',str(f)]];host=[(int(x[-1]),int(x[2]))for x in ev if x[:2]==['host',str(f)]];tiles=[(int(x[-1]),*map(int,x[2:5]))for x in ev if x[:2]==['tile',str(f)]]
  def durations(seq,bits):
   return sum((seq[i+1][0]if i+1<len(seq)else end)-time for i,(time,flags)in enumerate(seq)if flags&bits==bits)
  def edges(seq,bits,period):
   # %t($time) has1ns rounding. Every transition is on the same clock;
   # rounding EACH interval recovers integer clocks (<1ns error/interval).
   return sum(round(((seq[i+1][0]if i+1<len(seq)else end)-time)/period)for i,(time,flags)in enumerate(seq)if flags&bits==bits)
  stalls=[];start=None
  for time,flags in nes+[(nes[-1][0],0)]:
   if flags&1 and start is None:start=time
   if not(flags&1)and start is not None:
    j=bisect.bisect_left([x[0]for x in tiles],time);n=tiles[j]if j<len(tiles)else None;stalls.append(dict(begin_ms=start/1e9,end_ms=time/1e9,duration_ms=(time-start)/1e9,next_tile=n[1:]if n else None));start=None
  pulses=[time for i,(time,flags)in enumerate(host)if flags&16 and(i==0 or not host[i-1][1]&16)];gaps=[pulses[i]-pulses[i-1]for i in range(1,len(pulses))]
  fixtures=js(BASE/f'probes/nes-jobs394/native04/{f}/fixture.json');e=list(csv.reader(read(d/'joint-events.csv').splitlines()));stores=[x for x in e if x[:2]==['stored394',str(f)]];assert len(stores)==len(fixtures);at=0;consuming=[]
  for j,store in zip(fixtures,stores):
   b=bytes.fromhex(j['data']);n=len(b);assert int(store[3])==n
   if n:
    times=pulses[at:at+n];assert len(times)==n;at+=n;record=bytes.fromhex(j['record']);begin=times[0];finish=int(store[-1]);overlap=sum(max(0,min(finish,round(s['end_ms']*1e9))-max(begin,round(s['begin_ms']*1e9)))for s in stalls)
    if record[9]<2:consuming.append(dict(region=record[9],canonical=u16(record,10),bytes=n,first_read_ms=begin/1e9,stored_ms=finish/1e9,tile_backpressure_during_read_to_receipt_ms=overlap/1e9))
  assert at==len(pulses)
  rows.append(dict(frame=f,tile_bytes_accepted=len(tiles),source_RAM_write_cycles=edges(nes,2,46561),plan_RAM_read_cycles=edges(nes,4,46561),same_NES_edge_source_write_plan_read_cycles=edges(nes,6,46561),tile_backpressure_ms=durations(nes,1)/1e9,host_queue_write_read_event_same_edge=edges(host,17,11904),host_packet_ingress_executor_packet_read_same_edge=edges(host,5,11904),host_packet_ingress_expected_write_same_edge=edges(host,3,11904),actual_read_events=len(pulses),minimum_read_gap_host_clocks=round(min(gaps)/11904),largest_tile_stalls=sorted(stalls,key=lambda x:-x['duration_ms'])[:6],tile_consume_intervals=consuming))
 # Existing whole remains the area evidence;the new per-block numbers are caps.
 caps=dict(host_RAM_executor=400,NES_source_plan_executor=280,SPI_bit_CRC_snapshot=240,queue_credit_and_namespace=100,tile_ownership_and_bridge=140,control_program_RAM_ports_decode=150,contingency=85);assert sum(caps.values())==1395
 _,groups=plans();material=[];ordinary_actual_max=0
 for serial,pp in groups.items():
  f=serial+904;jobs=js(BASE/f'probes/nes-jobs394/arm10/jobs{f}.json');actual=[];expected=[];ordinary_actual_max=max(ordinary_actual_max,max((max(j['fragments']or[0])for j in jobs if j['region']>=2),default=0))
  for j in jobs:
   if j['region']<2:
    assert 0<j['decoded']<=2048 and j['decoded']%(32 if j['region']else 16)==0
    actual.extend((j['region'],j['canonical']+i)for i in range(j['decoded']//(32 if j['region']else 16)))
  for command in pp:
   if command[0]==7:
    k=command[1];unit=32 if k else 16;assert u16(command,10)%unit==0
    expected.extend((k,u16(command,10)//unit+i)for i in range(u16(command,14)//unit))
  assert actual==expected
  material.append(dict(frame=f,tile_jobs=sum(j['region']<2 for j in jobs),tile_bytes=sum(j['decoded']for j in jobs if j['region']<2),largest_job=max((j['decoded']for j in jobs if j['region']<2),default=0),tile_stamps=len(actual)))
 # The last decoded plan returns the mailbox before tile_done. Hence33,
 # not32:one running plan+16 sealed mailbox plans+16 pending host plans.
 lookahead=max([r+(16 if r==1 else 0)+16 for r in range(1,17)]+[32]);assert lookahead==33
 cases=[]
 for kind in (0,1):
  unit=32 if kind else 16
  for size in range(unit,2049,unit):
   for queued in range(lookahead+1):
    payload=size+queued*32+32;stamps=size//unit+queued+1
    assert payload<=3584 and stamps<=192
    cases.append((payload,stamps))
 max_payload=max(x[0]for x in cases);max_stamps=max(x[1]for x in cases);assert(max_payload,max_stamps)==(3136,162)
 frontier_cases=0
 for accounted in (0,1,15,16,31,32,33,34,82,128):
  for published in range(161):
   for count in range(1,17):
    allowed=published+count<=accounted+33;debt=max(0,published+count-accounted)
    assert allowed==(debt<=33);frontier_cases+=1
 layout=dict(tile_payload=[0,3583],ordinary_payload=[3584,4095],mailbox_payload=[0,31],tile_stamps=[32,799],host_context=[800,927],NES_source_context=[928,959],NES_plan_context=[960,1023])
 for keys in [('tile_payload','ordinary_payload'),('mailbox_payload','tile_stamps','host_context','NES_source_context','NES_plan_context')]:
  intervals=[layout[k]for k in keys];assert all(intervals[i][1]+1==intervals[i+1][0]for i in range(len(intervals)-1))
 debt=old['live']['failure_time_ms']-5371247*46561/1e9;period=357368*46561/1e9
 old_events=list(csv.reader(read(BASE/'probes/nes-plan390/joint04/joint-events.csv').splitlines()));new_events=list(csv.reader(read(d/'joint-events.csv').splitlines()))
 first_obj=next(x for x in new_events if x[:3]==['romtile305','905','1']);last_old_obj=[x for x in old_events if x[:3]==['romtile305','905','1']][-1]
 close_cycle=int(first_obj[4])//357368*357368+354640;close_ms=(int(first_obj[-1])+(close_cycle-int(first_obj[4]))*46561)/1e9
 window=dict(first_OBJ_ms=int(first_obj[-1])/1e9,upper_ROM_close_ms=close_ms,old392_last_OBJ_ms=int(last_old_obj[-1])/1e9,old_critical_headroom_ms=close_ms-int(last_old_obj[-1])/1e9,provisional_additional_critical_work_cap_ms=.100,one_additional_E2_14B_wire_ms=14*8/2.625e6*1000,not_a_new_ROM_schedule=True)
 controls=old['whole'];same_time=int(re.search(r'Time: (\d+) ps',log)[1])/1e9;delta=same_time-old['live']['failure_time_ms'];assert delta==0
 for name in ('nes_refill267.c','nes_bind287.c','nes_native289.c'):read(BASE/'probes/nes-jobs394/joint09'/name)
 for q in(ROOT/'tools/analyze_nes_owners395.py',ROOT/'tools/probe_nes_owners395.py',ROOT/'tests/nes-owners395/ports.svh',ROOT/'docs/nes-owners395-contract.ko.md',ROOT/'docs/nes-owners395-plan.json'):read(q)
 report=dict(audit_passed=True,new_implementation=False,new_MAP=False,production_selected=False,scope=__doc__,passive_trace=dict(rows=rows,startup_failure_ms=same_time,delta_vs394_ms=delta,model_still_fails907=True),actual_whole394=controls,proposed=dict(comb_caps=caps,control_total=sum(caps.values()),retained_codec_checker=2347,outside=11511,whole_target=15253,net_required_deletion=2321,FF_whole_ceiling=8985,RAM_bits_arithmetic=300640+(1024-32)*8+512*18,program_words_provisional=512,program_word_bits=18,physical_M9K_delta_and_FIT_unproven=True,layout=layout),ownership_model=dict(enumerated_cases=len(cases),legal_job_max=2048,maximum_unobserved_plan_lookahead=lookahead,mailbox_bytes=32,maximum_payload_debt=max_payload,tile_payload_capacity=3584,payload_margin=3584-max_payload,maximum_stamp_debt=max_stamps,stamp_capacity=192,stamp_margin=192-max_stamps,ordinary_reserved=512,maximum_ordinary_fragment=512,actual_max_ordinary_fragment=ordinary_actual_max,metadata_stamp_bytes=4,guards=['2 fixed one-extent banks rejected:3 legal gapped tiles exhaust descriptors at32bytes','no ordinary reserve rejected:two ordinary heads may block their later TILE record;256B also fails actual480B repeat','32plan lookahead rejected:mailbox releases at last CHECK before tile_done','publish before binding/CRC/actualread/receipt rejected','late STOP write or finalACK beforePPU/VBlank rejected'],conditional_on=['ARM accounts accepted plans and finalizes a TILE span at<=2048B','at most1 active ordinary fragment','mailbox/stamp ownership admits only current lease generation','33plan bound includes current+sealed+pending banks','credit is storage credit;consumption and PPU completion remain separate']),timing_admission=dict(startup_debt_ms=debt,one_ROM_period_ms=period,remaining_if_exactly_one_period_recovered_ms=period-debt,one_period_recovery_is_NOT_prediction=True,cold905_OBJ_window=window,additional_SPI_wire_format_bytes=0,E2_IRQ_count_changes_unmeasured=True,warm_same_actual_phase_pair_not_reached=True,decoder_word_latency_and_RAM_arbitration_unmeasured=True),material71=material,pins=pins)
 report['ownership_model']['ARM_publication_frontier']=dict(required=True,formula='published+next_batch_count<=accounted+33',reserve_before_SPI=True,account_only_after_at290_commit=True,nonblocking_yield_when_full=True,accounted_may_exceed_published=True,model_cases=frontier_cases,proposed_static_bytes=8,actual_new_M4_compile_and_schedule=False)
 assert ordinary_actual_max==480
 for n in range(1,3419):
  fragments=[min(512,n-at)for at in range(0,n,512)];assert sum(fragments)==n and max(fragments)<=512
 report['ownership_model']['repeat_fragmentation']=dict(decoded_cap=512,arithmetic_sizes=3418,larger_than512_internal_fragments=True,wire_record_unchanged=True,source_consumed_counter_updates_last_fragment_only=True,new_lifecycle_RTL_tested=False)
 report['ownership_model']['capacity_scope']='unpublished-record dependency prefix,not all outstanding bytes;known descriptors must drain full FIFO'
 report['ownership_model']['design_rules_not_new_RTL_tests']=report['ownership_model'].pop('guards')
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(audit_passed=True,passive=rows,caps=caps,ownership=report['ownership_model'],timing=report['timing_admission']),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
