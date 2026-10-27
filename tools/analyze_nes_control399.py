# SPDX-License-Identifier: MIT
"""399 boundary/port audit and separate header-DMA component/whole costs.
No claimed new combined ARM/RTL schedule or demonstrated1172 engine.
"""
import argparse,collections,csv,json,re
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha

HOST=['cycles','read_accept','read_end','read_pending_cycles','ctx_reads','ctx_writes','ctx_wait_cycles','header_grants','header_wait_cycles','stage_atomic_cycles','tile_copy_writes','stamp_writes','binding_cycles','tile_mailbox_returns','stage_consumes','queue_publish','queue_retire','queue_consume','queue_event_cycles','interpreter_IRQ_cycles','interpreter_memory_cycles','interpreter_IO_cycles','source_footer_cycles','chunk_opens','finish_pending_cycles','tile_mailbox_backpressure_cycles','ctx_vs_stage_atomic_cycles','header_vs_stage_atomic_cycles','read_rejected','TAKE_program_commands','reserved30','reserved31']
NES=['cycles','source_RAM_writes','source_footer_request_cycles','source_record_backpressure_cycles','plan_read_request_cycles','plan_captures','source_plan_request_overlap_cycles','source_footer_captures','tile_output_backpressure_cycles','ROM_qualified_cycles','all_ROM_grants','hint_ROM_grants','nonhint_ROM_grants_including_core','core_requests','hint_metadata_read_cycles','reserved15']

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,default=BASE/'probes/nes-control399');p.add_argument('--out',type=Path,default=ROOT/'analysis/control399-verification.json');a=p.parse_args();d=a.evidence.resolve();pins={}
 def pin(q):pins[q.relative_to(BASE).as_posix()]=sha(q);return sha(q)
 def read(q):pin(q);return q.read_text(encoding='utf-8-sig')
 def js(q):return json.loads(read(q))
 for run in('trace01','native01','map01'):
  archive=js(d/run/'archive399-v3.json');assert archive['run']==run and archive['raw_logs_unfiltered']
  assert archive['files']['result.json']['sha256']==pin(d/run/'result.json')
 assert 'nes_run_observer134.sv'in js(d/'map01/archive399-v3.json')['files']
 baseline=js(ROOT/'analysis/joint398-verification.json');assert baseline['audit_passed']and not baseline['time_goal_met']and not baseline['area_goal_met']
 tr=d/'trace01';ref=BASE/'probes/nes-joint398/live11';m=js(tr/'manifest399.json');rr=js(tr/'result.json')
 assert rr['audit_passed']and rr['timeline_exact398']and not rr['implementation_changed']and not rr['new_MAP']
 assert pin(tr/'joint-events.csv')==pin(ref/'joint-events.csv')and pin(tr/'arm-worker.log')==pin(ref/'arm-worker.log')
 assert pin(tr/'output.elf')==m['ELF']==pin(ref/'output.elf');assert pin(tr/'program398.hex')==m['program']==pin(ref/'program398.hex')
 assert m['test']==pin(tr/'joint266_tb.sv')and m['monitor']==pin(ROOT/'tests/nes-control399/ports.svh')
 assert len(m['RTL'])==33 and all(pin(tr/n)==h==pin(ref/n)for n,h in m['RTL'].items())
 log=read(tr/'vsim.log');assert 'Fatal: capture coverage367'in log and 'FAULT398'not in log
 for f in range(905,917):assert pin(tr/f'arm{f}.json')==pin(ref/f'arm{f}.json')
 ports=tr/'ports399.csv';pin(ports);h={};n={};reads=[];control=collections.Counter();source_rows=0;gates={};execute={};publication=[]
 with ports.open()as f:
  for r in csv.reader(f):
   if r[0]=='host_count':h.setdefault(int(r[1]),{})[HOST[int(r[2])]]=int(r[3])
   elif r[0]=='NES_count':n.setdefault(int(r[1]),{})[NES[int(r[2])]]=int(r[3])
   elif r[0]=='read':reads.append(dict(frame=int(r[1]),at=int(r[2]),position=int(r[3]),region=int(r[4]),ps=int(r[5])))
   elif r[0]=='control_read':control[int(r[2])]+=1
   elif r[0]=='source':source_rows+=1
   elif r[0]=='display_gate':gates[int(r[1])]=dict(phase=int(r[2]),cut_line=int(r[3]),tail_budget=int(r[4]),blank=bool(int(r[5])),ms=int(r[6])/1e9)
   elif r[0]=='display_execute':execute[int(r[1])]=int(r[3])/1e9
   elif r[0]=='publication':publication.append(dict(frame=int(r[1]),phase=int(r[2]),token=int(r[3]),FIFO_bytes=int(r[4]),stamps=int(r[5]),accepted=int(r[6]),retired=int(r[7]),ms=int(r[8])/1e9))
 assert sorted(h)==sorted(n)==list(range(905,917));assert all(v['read_rejected']==0 and v['read_accept']==v['read_end']for v in h.values())
 assert len(reads)==sum(v['read_accept']for v in h.values())
 spacing=[y['ps']-x['ps']for x,y in zip(reads,reads[1:])if x['frame']==y['frame']and y['at']==x['at']+1]
 assert spacing and min(spacing)>0
 # Component trial uses identical semantic fixtures; timeline waits, ARM,
 # source/plan credit and ROM competition are NOT retimed by subtracting this.
 native=d/'native01';nr=js(native/'result.json');assert nr['passed']and not nr['fullresident']and nr['WRAM']['total']==15360
 cpu=[];clocks=46561/1e9
 for item in nr['cases']:
  f=item['frame'];stop=item.get('STOP',False);q=native/(str(f)+('-stop'if stop else''));pin(q/'spool.sfc');pin(q/'capture.lua');pin(q/'mesen.log')
  if stop:assert not item['final_ACK']and item['PPU_jobs']==0;continue
  assert item['body_bytes']==1778 and not item['synthetic_tile_bytes'];old=BASE/'probes/nes-jobs394/native04'/str(f)
  assert pin(q/'fixture.json')==pin(old/'fixture.json')
  totals=[];widths=[]
  for path in(old,q):
   rows=[list(map(int,r))for r in csv.reader(read(path/'events.csv').splitlines())];jobs=js(path/'fixture.json');intervals=[];headers=[]
   for i in range(1,len(jobs)+1):
    ev=[r for r in rows if r[0]==i];start=next(r[4]for r in ev if r[1:3]==[0,0x6001]);end=next(r[4]for r in ev if r[1:4]==[1,0x6050,0xa5]);intervals.append(end-start)
    hdr=[r[4]for r in ev if r[1]==0 and 0x6080<=r[2]<=0x6090];assert len(hdr)==17;headers.append(hdr[-1]-hdr[0])
   totals.append(sum(intervals));widths.append([min(headers),max(headers)])
  assert totals[1]<totals[0];cpu.append(dict(frame=f,jobs=len(jobs),old_source_service_clocks=totals[0],DMA_header_source_service_clocks=totals[1],saved_clocks=totals[0]-totals[1],saved_ms=(totals[0]-totals[1])*clocks,header17_span_old=widths[0],header17_span_DMA=widths[1],not_whole_schedule_gain=True))
 mp=d/'map01';mr=js(mp/'result.json');assert mr['passed']and not mr['undriven']and not mr['FIT']and not mr['STA']
 labels=dict(LE='Total logic elements',comb='Total combinational functions',FF='Dedicated logic registers',RAM_bits='Total memory bits')
 whole={k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',mr['summary'])[1].replace(',',''))for k,v in labels.items()}
 assert whole==baseline['whole']['joint398']
 assert all(pin(mp/name)==hash for name,hash in m['RTL'].items());assert pin(mp/'program398.hex')==m['program']
 image=(native/'905/spool.sfc').read_bytes();assert bytes(int(x,16)for x in read(mp/'sink-program.hex').split())==image[:0xfc0]+image[0x7fc0:0x8000]
 deficits=[]
 for f in(914,915):
  gate=gates[f];actual=next(r for r in baseline['timing']['actual']['present']if r['frame']==f);target=actual['VBlank']-1
  latest=(target*357368+min((gate['cut_line']+1)*1364-1,357368-gate['tail_budget']))*clocks
  saving=next(r['saved_ms']for r in cpu if r['frame']==f)
  deficits.append(dict(frame=f,target_VBlank=target,gate_ms=gate['ms'],latest_gate_ms=latest,required_advance_ms=gate['ms']-latest,header_DMA_component_saved_ms=saving,optimistic_same_origin_remainder_ms=gate['ms']-latest-saving,not_retimed_or_bound=True))
 calls=js(ref/'calls337.json')
 finish=next(r for r in calls if r['name']=='finish267'and 400e6<r['start']['modeled_ns']<401e6)
 receive=next(r for r in calls if r['name']=='source_receive367'and 415e6<r['start']['modeled_ns']<416e6)
 overlap=dict(frame_waiting_display=914,next_input=915,finish_start_ms=finish['start']['modeled_ns']/1e6,finish_end_ms=finish['end']['modeled_ns']/1e6,observed_wait_ms=(finish['end']['modeled_ns']-finish['start']['modeled_ns'])/1e6,next_receive_start_ms=receive['start']['modeled_ns']/1e6,next_receive_end_ms=receive['end']['modeled_ns']/1e6,next_receive_observed_ms=(receive['end']['modeled_ns']-receive['start']['modeled_ns'])/1e6,old_output_pending_at_finish=finish['start']['pending'],old_output_sent=finish['start']['sent'],old_output_retired=finish['start']['retired'],not_a_measured_prefetch_gain=True)
 assert overlap['old_output_pending_at_finish']==0 and overlap['old_output_sent']==overlap['old_output_retired']==304
 for name in('executed-worker367.py','nes_input286.inc','nes_native289.inc','nes_refill267.c','nes_output264.c','nes_source368.c'):pin(ref/name)
 for path in(ROOT/'tools/probe_nes_control399.py',ROOT/'tools/probe_nes_header399_native.py',ROOT/'tools/map_nes_control399.py',ROOT/'tools/analyze_nes_control399.py',ROOT/'tools/archive_nes_control399.py'):pin(path)
 pending=baseline['timing']['next_capture_ownership_debt']
 candidates=[dict(name='more input storage/early storage credit only',time='can move a capture ownership boundary; cannot repair skipped presentation VBlanks alone',new_whole_cost=None,accepted=False),dict(name='17B header DMA alone',time='actual CPU component saving measured; no live ARM/SPI/IRQ/credit retiming',new_whole_cost=whole,control=3471,over_1172=2299,accepted=False),dict(name='fixed transaction ingest + one read completion owner + separate receive/display commit',time='proposed next scope with header DMA and early next-input receive after output publication',new_whole_cost=None,control=None,required_control_cap=1172,accepted=False,reason='must delete the interpreter and physical IO mux/control together; no fit claim from proposed caps')]
 report=dict(audit_passed=True,combined_solution_proven=False,new_live_implementation=False,new_live_gain=False,FIT=False,STA=False,hardware_ready=False,scope=__doc__,selected=dict(passive='trace01',native='native01',whole_map='map01'),baseline398_timeline_exact=True,whole399_header_DMA=whole,whole_delta_vs398={k:0 for k in whole},control=dict(actual=3471,cap=1172,over=2299,new_engine_measured=None),CPU_header_DMA=dict(cases=cpu,STOP=True,body_bytes=1778,old_body_bytes=1738,additional_WRAM=0,existing_WRAM=15360,fullresident=False,combined_timing=False),ports=dict(host=h,NES=n,read_events=len(reads),minimum_observed_read_spacing_ps=min(spacing),minimum_observed_read_spacing_host_cycles=min(spacing)/11904,read_pending_host_cycles=sum(r['read_pending_cycles']for r in h.values()),source_transition_rows=source_rows,control_reads={f'{a:06x}':v for a,v in sorted(control.items())},observed_spacing_not_WCET_or_read_end_budget=True),display_gates=deficits,capture917=pending,candidates=candidates,proposed_RAM_ownership=dict(payload_4KiB=['host A:tile/ordinary writes','host B:latched actual SNES read'],metadata_1KiB=['host A:stage + immutable header arbitration','NES B:tile mailbox write + hint tags'],source_1KiB=['NES write','host SPI read; pinned head'],plan_1KiB=['host unpublished bank write','NES sealed bank read'],status_RAM='replace freed control ROM space with prebuilt dual snapshot banks; not another port on metadata'),proposed_receive_overlap=dict(start_after='all current output records published; no wire_busy or pending payload owner',retain=['old display lease/fence until exact final ACK','current plan-retire namespace','last successfully displayed resident validity'],snapshot_required=['old receiver epoch/serial/raw_count for publish352','new raw-group and geometry-group tracking','pending receive-valid identity'],unsafe_shortcut='calling source_receive while publish352 still reads live receiver280 would publish the next input as displayed',ARM_bytes_and_cycles=None,implemented=False),first_hardware_test=dict(available_now=False,earliest_stage='after fitting actual whole image, new clock/IO timing checks and paired resident ARM/65816 package',does_not_require='MMC4/MMC5 or final sustained60fps for a bounded first diagnostic',calendar_estimate=None,reason='1172 implementation and fitting image do not exist yet; no defensible day estimate',avoid_repeating='old227/044 boot tests or a generic diagnostic detour'),pins=pins)
 report['proposed_receive_overlap']['observed_opportunity']=overlap
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',newline='\n')
 print(json.dumps(dict(audit_passed=True,combined_solution_proven=False,whole=whole,read_events=len(reads),min_read_host_cycles=min(spacing)/11904,CPU_component=cpu,display_gates=deficits),indent=2))
if __name__=='__main__':main()
