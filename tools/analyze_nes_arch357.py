# SPDX-License-Identifier: MIT
"""Design budgets from pinned338/355/356 evidence. No new RTL or timing claim."""
import csv,json,itertools,math
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha

def cancel_model():
 events=('stop','collector_ack','deliver_done','drain_rows','retire_done','publish','restart','reply')
 normal=0;blocked=0
 for order in itertools.permutations(events):
  s=dict(stop=False,epoch=0,query=True,collector_ack=False,inflight=True,done=None,delivered=False,rows=2)
  def step(e):
   nonlocal normal,blocked
   if e=='stop':s['stop']=True
   elif e=='collector_ack' and s['stop']:s['collector_ack']=True;s['query']=False
   elif e=='reply' and not s['stop'] and s['epoch']==0:s['query']=False
   elif e=='deliver_done' and not s['delivered']:s['delivered']=True;s['inflight']=False;s['done']=0
   elif e=='drain_rows':s['rows']=0 # validated normal consumption or cancelled discard
   elif e=='retire_done' and s['stop']:s['done']=None
   elif e=='publish':
    accepted=s['done']==s['epoch'] and not s['stop'] and not s['query'] and not s['inflight'] and s['rows']==0
    if accepted:assert s['epoch']==0;normal+=1;s['done']=None
    else:blocked+=1
   elif e=='restart':
    drained=s['stop'] and s['collector_ack'] and not s['query'] and not s['inflight'] and s['done'] is None and s['rows']==0
    if drained:s['epoch']+=1;s['stop']=False
  for e in order:step(e)
  if s['epoch']==0:
   for e in ('stop','collector_ack','deliver_done','drain_rows','retire_done','restart'):step(e)
  assert s['epoch']==1 and not s['inflight'] and not s['query'] and s['rows']==0
  step('reply');step('deliver_done');step('publish') # stale epoch0 cannot publish after restart
  assert s['done'] is None
 return dict(permutations=math.factorial(8),normal_publications=normal,blocked_publications=blocked,scope='Bounded abstract protocol, one stale namespace and two row slots; not RTL/CDC/metastability proof. Event ordering is logical, no clock latency asserted.',clock_stopped_rule='Without collector cancellation ack restart is forbidden; no timeout may synthesize it.')

def main():
 pins={}
 def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
 def js(p):return json.loads(read(p))
 base=js(ROOT/'analysis/raster355-verification.json');rejected=js(ROOT/'analysis/query356-verification.json');area=js(ROOT/'analysis/ingress338-verification.json');ports=js(ROOT/'analysis/boundary353-verification.json')
 assert base['whole']['comb']==17274 and not rejected['candidate_selected'] and rejected['guards']['failed_case_numbers']==[24,26]
 rows=[]
 for tag in ('window01','fixed01','normal01'):
  d=BASE/'probes/nes-raster355'/tag;r=js(d/'result.json');assert r['passed']
  for n,h in r['rtl_hashes'].items():assert sha(d/n)==h;read(d/n)
  ev=list(csv.reader(read(d/'joint-events.csv').splitlines()));cost=[int(x,16) for x in read(d/'transaction-cost280.hex').split()]
  for frame in (905,906,907):
   e=[x for x in ev if len(x)>1 and x[1]==str(frame)];first=lambda name:next(x for x in e if x[0]==name)
   start=int(first('start319')[2]);finish=int(first('frame_done')[2]);input_end=int(first('input_done337')[-1]);last=None;mandatory=0.;wire_bytes=0;decode=0;polls=0;prefix_reply=0;packets=0
   for x in e:
    if x[0]=='input_begin337':last=x
    if x[0]=='input_wire337' and x[3]=='0':
     if x[4]=='0':polls+=1;continue
     token=int(last[2])+int(last[3]);instructions=int(last[5])+cost[token*5+4]
     prefix_reply+=instructions;wire_bytes+=int(x[5]);packets+=1
     mandatory+=int(x[5])*8/2625+instructions/84000+0.008
    if x[0]=='input_decode337':decode+=int(x[3]);mandatory+=int(x[3])/84000
   prev={};gaps=[]
   for x in e:
    if x[0]=='read336':
     token=x[2];t=int(x[-1])
     if token in prev:gaps.append((t-prev[token])/1000)
     prev[token]=t
   req=next(x for x in e if x[0]=='firstreq305' and x[2]=='0');accept=next(x for x in e if x[0]=='rom_accept327' and x[2]=='0')
   stage=first('stage325');total=(finish-start)/1e9;inputms=(input_end-start)/1e9
   end_cycle=((int(req[3])-354640)//357368)*357368+354640
   end_relative_ms=(end_cycle-int(first('start319')[3]))*45.454/1e6
   conservative_end_upper_ms=end_relative_ms+2*45.454/1e6 # counter/event observation uncertainty, two NES clocks
   rows.append(dict(previous_ROM_window_end_approx_ms=end_relative_ms,previous_ROM_window_end_upper_ms=conservative_end_upper_ms,mode=tag,frame=frame,total_ms=total,gap_ms=total-1000/60,start_ps=start,start_ROM_cycle=int(first('start319')[3]),first_BG_ms=(int(req[-1])-start)/1e9,ROM_accept_ms=(int(accept[-1])-start)/1e9,post_ROM_ms=(finish-int(accept[-1]))/1e9,input_ms=inputms,mandatory_prefinal_source_ms=mandatory,max_input_saving_ms=inputms-mandatory,nonempty_source_SPI_bytes=wire_bytes,nonempty_source_packets=packets,decoder_instructions=decode,prefix_reply_instructions=prefix_reply,empty_polls=polls,min_read_interval_ns=min(gaps),expanded_bytes=int(stage[2])))
 fixed=next(x for x in rows if x['mode']=='fixed01' and x['frame']==907)
 continuous=next(x for x in rows if x['mode']=='window01' and x['frame']==907)
 assert continuous['mandatory_prefinal_source_ms']>continuous['previous_ROM_window_end_upper_ms']
 firstgap=.873217;remaining=firstgap-fixed['max_input_saving_ms']
 assert abs(fixed['mandatory_prefinal_source_ms']-2.2011904761904764)<1e-10 and remaining>0
 # The source uses delta[0..65], header/trailer[256..275], mask[384..392].
 used=set(range(66))|set(range(256,276))|set(range(384,393));banks=[set(range(128,194)),set(range(288,354))]
 assert not banks[0]&banks[1] and all(not b&used for b in banks) and max(set.union(*banks))<512
 timing=dict(host_MHz=84,NES_MHz=22,raw_final_cycles=1956,raw0_final_cycles=1856,raw_final_extra_us=1956*(1/22-1/84),raw0_final_extra_us=1856*(1/22-1/84),six_cycle_read_ns=6000/22,eight_cycle_read_ns=8000/22,min_observed_read_ns=min(x['min_read_interval_ns'] for x in rows),literal_three_cycle_MBps=22/3,repeat_one_cycle_MBps=22,SPI_MBps=2.625/8)
 assert timing['min_observed_read_ns']>timing['six_cycle_read_ns']
 for n in ('nes_core257.sv','nes_mux260.sv','nes_queue260.sv','nes_validator278.sv','nes_native_frame201.sv','nes_joint257.sv'):read(BASE/'probes/nes-raster355/fixed01'/n)
 read(BASE/'probes/nes-ingress338/board01/output_files/board.map.rpt');read(BASE/'probes/nes-query356/map01/output_files/board.map.rpt')
 read(ROOT/'tools/analyze_nes_arch357.py')
 budget=dict(whole_baseline=area['whole'],whole_cap=15253,device_comb=15408,required_net_deletion=2021,source_host_current=3908,source_host_cap=2035,queue_SPI_current=798,queue_SPI_cap=650,checker_aperture_retained=1159,plan_retained=459,outside_retained=10950,A=dict(source_transport=399,new_CDC_cancel_allowance=100,common_executor_cap=1536),B=dict(direct_transport_allowance=335,row_producer_CDC_cancel_allowance=200,common_executor_cap=1500),status='Acceptance allocations, NOT estimated or measured new synthesis savings. New additions must fit inside caps; baseline outside cannot silently pay for them.')
 assert sum(budget[x] for x in ('source_host_cap','queue_SPI_cap','checker_aperture_retained','plan_retained','outside_retained'))==budget['whole_cap']
 assert sum(budget['A'].values())==sum(budget['B'].values())==2035
 result=dict(stage=357,analysis_passed=True,selected_RTL=338,selected_ARM=355,implementation_selected=False,priority='A boundary feasibility first; B is comparison/fallback, not selected',rows=rows,time_budget=dict(first_ROM_gap_ms=firstgap,continuous_previous_window_end_upper_ms=continuous['previous_ROM_window_end_upper_ms'],continuous_source_floor_excess_ms=continuous['mandatory_prefinal_source_ms']-continuous['previous_ROM_window_end_upper_ms'],continuous_first_ROM_after_deadline_ms=continuous['ROM_accept_ms']-1000/60,continuous_contract_change_required=True,A_fixed_phase_ARM_advance_required_ms=firstgap,B_best_case_source_saving_ms=fixed['max_input_saving_ms'],B_fixed_phase_additional_ARM_advance_required_ms=remaining,B_min_additional_ARM_instructions=math.ceil(remaining*84000),post_ROM_gap_ms=.653568,limits='A keeps338 source schedule; B assumes unchanged canonical source bytes. Serial mandatory nonempty SPI + existing measured ARM source decode/prefix/reply + retained CS delays. Excludes final D5 entirely and removes all empty polls/codec wait: optimistic lower bound under unchanged N5/MASK/SHIFT/ARM355, not new execution/WCET.'),budget=budget,A_timing_sensitivity=timing,B_rows=dict(normal_blocks=68,max_blocks=76,mailbox_publications_warm=68,mailbox_roundtrips_max=152,storage_bytes=132,phase_RAM_relative_banks=[128,288],physical_banks=[640,800],new_M9K_only_if_port_reuse_fails=1,port_requirement='A fixed NES row producer; B fixed host common source/validator phase owner, initializer precedes source. Cannot mux clocks. Serialize row read and delta/mask/header writes; preserve output H2 lifetime.'),cancel_model=cancel_model(),prior_port_scope='353 passive traces use same338 RTL but352 ARM; no new355 timing derived from353 host activity.',new_RTL=False,new_ARM=False,new_MAP=False,new_scheduled_run=False,FIT=False,STA=False,physical=False,pins=pins)
 (ROOT/'analysis/arch357-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
 print(json.dumps(dict(time_budget=result['time_budget'],A_timing=timing,budget=budget,model=result['cancel_model'],pins=len(pins)),indent=2))
if __name__=='__main__':main()
