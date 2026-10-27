# SPDX-License-Identifier: MIT
"""397 replacement boundary/port admission audit. No new execution RTL or MAP.
396 actualM4/native-service timeline is preserved,including first missed911.
Caps and cycle allocations are admission requirements,not measured savings.
"""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha

HOST=[('record_or_final_view',12),('immutable_lease',12),('DMA_cursors',16),('repeat_seed',4),('queue_counters',8),('source_head',8),('status_bank_A',24),('status_bank_B',24),('manifest_and_dispatch',16),('three_saved_9bit_PCs',4)]
SOURCE=[('footer',6),('CRC_checkpoint',2),('cursor_and_flags',4),('ack_checkpoint',4),('saved_PCs',4),('scratch',10),('spare',2)]
PLAN=[('normalized_plan_16rowbytes_8x16bit_ALT_tags',42),('cursors',8),('bank_ownership',4),('current_row',4),('saved_PCs',4),('scratch',2)]
SPI=[('request_fields',8),('CRC_checkpoints',4),('ALU_scratch',8),('publication_flags',4),('mailbox_checkpoints',8),('spare',8)]
CAPS=dict(host_and_descriptor_byte_executor=270,NES_source_plan_and_EA_hint_executor=355,SPI_bit_shift_serialCRC_IRQ=220,queue_credit_namespace=80,tile_mailbox_bridge=43,program_context_and_physical_bus_ports=150,contingency=54)

def layout(first,items):
 rows=[]
 for name,n in items:rows.append(dict(name=name,first=first,last=first+n-1,bytes=n));first+=n
 return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--out',type=Path,default=ROOT/'analysis/control397-verification.json');a=p.parse_args();d=a.trace.resolve();pins={}
 def pin(q):pins[q.relative_to(BASE).as_posix()]=sha(q);return pins[q.relative_to(BASE).as_posix()]
 def read(q):pin(q);return q.read_text(encoding='utf-8-sig')
 def js(q):return json.loads(read(q))
 base=js(ROOT/'analysis/joint396-verification.json');assert base['audit_passed']and base['whole']['candidate396']['comb']==18108
 m=js(d/'manifest397.json');result=js(d/'result.json');assert result['audit_passed']and not result['implementation_changed']and result['timeline_exact396']
 assert m['RTL']==base['matching_whole_functional_RTL']and len(m['RTL'])==32
 for n,h in m['RTL'].items():assert pin(d/n)==h
 assert pin(d/'output.elf')==m['ELF'];assert pin(d/'joint-events.csv')==pin(BASE/'probes/nes-joint396/live07/joint-events.csv')
 ref=BASE/'probes/nes-joint396/live07'
 assert pin(d/'producer263.dll')==pin(ref/'producer263.dll')and pin(d/'arm-worker.log')==pin(ref/'arm-worker.log')
 for f in range(905,909):assert pin(d/f'arm{f}.json')==pin(ref/f'arm{f}.json')
 for q in d.glob('jobs394-*.hex'):assert pin(q)==pin(ref/q.name)
 assert pin(d/'joint266_tb.sv')==m['test']and m['monitor']==pin(ROOT/'tests/nes-control397/ports.svh')
 log=read(d/'vsim.log');assert 'Fatal: next capture deadline missed367 frame911'in log and 'Time: 316648557725 ps'in log
 # Exact self boundaries only; never add inclusive parent costs.
 rpt=read(BASE/'probes/nes-joint396/map03/output_files/board.map.rpt');self_cost={}
 for line in rpt.splitlines():
  c=[x.strip()for x in line.split(';')]
  if len(c)>4 and re.fullmatch(r'\|[^|]+\|',c[1])and re.fullmatch(r'\d+ \(\d+\)',c[2]):self_cost[c[1].strip('|')]=int(re.search(r'\((\d+)\)',c[2])[1])
 old=dict(host_and_bounds=self_cost['nes_output260:flow']+self_cost['nes_check396:record_check'],NES_source_plan_hint=sum(self_cost[n]for n in('nes_transport257:transport','nes_plan_batch206:transport','nes_plan_spi200:endpoint','nes_walk396:execution','nes_hint361:hint')),SPI=self_cost['nes_spi270:spi_front270'],queue=self_cost['nes_queue260:queue'],tile=self_cost['nes_tile_link394:tile_link'])
 assert old==dict(host_and_bounds=2050,NES_source_plan_hint=1015,SPI=700,queue=219,tile=43)
 assert sum(old.values())==4027 and sum(CAPS.values())==1172
 assert 11730+2351+1172==15253 and 4027-1172==2855
 # Cold/context register packing,not a new synthesized register file.
 packing=dict(host=layout(800,HOST),NES_source=layout(928,SOURCE),NES_plan=layout(960,PLAN),SPI_queue_scratch=layout(472,SPI))
 assert [packing[k][-1]['last']for k in packing]==[927,959,1023,511]
 allctx=[a for k in('host','NES_source','NES_plan')for row in packing[k]for a in range(row['first'],row['last']+1)]
 assert sorted(allctx)==list(range(800,1024))and len(set(allctx))==224
 assert 'expected_address313<472'in read(d/'nes_queue260.sv')
 # The proposed512x18 control RAM uses8 data-only words for seven immutable EA tags.
 # Both clocks retain their one physical port; a tag access steals a fetch.
 for n in range(1,8):
  addr=list(range(504,504+n));assert len(set(addr))==n and all(504<=x<512 for x in addr)
 assert all((x>=504)==(x not in range(504))for x in range(512))
 rows=list(csv.reader(read(d/'ports397.csv').splitlines()));assert rows[-1][0]=='end';end=int(rows[-1][-1]);nes=[r for r in rows if r[0]=='nes'];host=[r for r in rows if r[0]=='host']
 def intervals(seq):return [(r,(int(seq[i+1][-1])if i+1<len(seq)else end)-int(r[-1]))for i,r in enumerate(seq)]
 ni=intervals(nes);hi=intervals(host);port_rows=[]
 for f in(905,906,907,908):
  def nclocks(mask):return sum(round(dt/46561)for r,dt in ni if int(r[1])==f and int(r[3])&mask==mask)
  def hclocks(mask):return sum(round(dt/(1e6/84))for r,dt in hi if int(r[1])==f and int(r[2])&mask==mask)
  dwell={state:sum(dt for r,dt in hi if int(r[1])==f and int(r[3])==state)/1e9 for state in range(33)}
  port_rows.append(dict(frame=f,NES_source_RAM_write_clocks=nclocks(4),NES_plan_read_demand_clocks=nclocks(8),same_edge_source_write_plan_read_clocks=nclocks(12),source_footer_demand_clocks=nclocks(16),plan_field_capture_clocks=nclocks(32),source_footer_plan_capture_same_edge=nclocks(48),host_ingress_expected_write_same_edge=hclocks(12),host_ingress_packet_read_same_edge=hclocks(20),host_prefill_context_binding_same_edge=hclocks(1536),nonwait_state_ms=sum(v for k,v in dwell.items()if k not in(0,14,15,31)),state_dwell_ms=dwell))
 gates=[]
 for f in(907,908):
  view=next(r for r in rows if r[:2]==['view_done',str(f)]);gate=next(r for r in rows if r[:2]==['display_gate',str(f)]);execute=next(r for r in rows if r[:2]==['display_execute',str(f)])
  time=int(gate[-1]);phase=int(gate[2]);cutoff=int(gate[3]);budget=int(gate[4]);target_window=16 if f==907 else 17;latest_phase=min((cutoff+1)*1364-1,357368-budget);latest=(target_window*357368+latest_phase)*46561
  gates.append(dict(frame=f,view_done_ms=int(view[-1])/1e9,CPU_postview_masterclocks=int(view[3]),gate_ms=time/1e9,gate_phase=phase,cutoff=cutoff,budget_masterclocks=budget,execute_ms=int(execute[-1])/1e9,wait_ms=(int(execute[-1])-time)/1e9,target_VBlank=target_window,target_latest_legal_gate_ms=latest/1e9,advance_to_target_latest_ms=max(0,(time-latest)/1e9),blank_at_gate=bool(int(gate[5]))))
 g908=gates[1];assert abs(g908['advance_to_target_latest_ms']-3.861194557)<1e-9
 source_rows=[]
 for sf in(907,908,909):
  full=sum(dt for r,dt in ni if int(r[2])==sf and int(r[3])&256)/1e9
  stalled=sum(dt for r,dt in ni if int(r[2])==sf and int(r[3])&512)/1e9
  source_rows.append(dict(source_frame=sf,ring_full_ms=full,record_stalled_ms=stalled))
 # EA is actual causal ARM traffic. Compute wire-only alternatives separately.
 a908=js(d/'arm908.json');ea=next(t for t in a908['transfers']if t['tx'].startswith('ea'));packet=bytes.fromhex(ea['tx']);assert len(packet)==28 and packet[1]==7
 tags=[int.from_bytes(packet[i:i+2],'little')for i in range(12,26,2)];distinct=list(dict.fromkeys(tags));assert len(distinct)==3
 eaend=next(r for r in rows if r[0]=='SS_end'and int(r[1])==908 and int(r[2])==234);eacmd=next(r for r in rows if r[0]=='command'and int(r[1])==908 and int(r[2])==234)
 eacycle=round(int(eaend[-1])/46561);close=(eacycle//357368*357368+354640)*46561;wire_saved=(28-(14+2*len(distinct)))*8/2.625e6*1000
 hint_rows=[r for r in rows if r[0]=='hint'and int(r[1])==908];grants=[r for r in rows if r[0]=='hint_grant'and int(r[1])==908];hd=next(r for r in rows if r[:2]==['hint_done','908'])
 assert hint_rows and grants
 hint=dict(frame=908,actual_bytes=28,actual_tags=tags,distinct_tags=distinct,command_end_ms=int(eaend[-1])/1e9,ROM_window_close_ms=close/1e9,headroom_ms=(close-int(eaend[-1]))/1e9,first_ROM_grant_ms=int(grants[0][-1])/1e9,first_ROM_grant_cursor=int(grants[0][2]),last_ROM_grant_ms=int(grants[-1][-1])/1e9,ROM_grants=len(grants),hint_complete_ms=int(hd[-1])/1e9,cursor_before_window_close=max((int(r[2])for r in hint_rows if int(r[-1])<=close),default=-1),variable_count_3_bytes=20,wire_only_saving_ms=wire_saved,variable_count_3_full_schedule_tested=False)
 for q in(ROOT/'tools/probe_nes_control397.py',ROOT/'tools/analyze_nes_control397.py',ROOT/'docs/nes-control397-contract.ko.md',ROOT/'docs/nes-control397-plan.json'):
  if q.exists():pin(q)
 report=dict(audit_passed=True,new_implementation=False,new_MAP=False,production_selected=False,time_goal_met=False,area_goal_met=False,scope=__doc__,baseline396_whole=base['whole']['candidate396'],narrow_boundary=dict(current_control=3872,retained=2351,outside=11885,cap=1017),expanded_hint_boundary=dict(current=old,total=4027,hint_moved_from_outside=155,outside=11730,retained=2351,caps=CAPS,cap=sum(CAPS.values()),whole_target=15253,remaining_with155reserve=2855,no_free155_saving=True),context_layout=packing,program=dict(words=512,bits=18,code_words=504,hint_data_words=[504,511],dual_clock_ports=2,host_tag_write_steals_fetch=True,NES_tag_read_steals_fetch=True,hardware_code_write_protection_required=True,RAM_bits_arithmetic=310112-1536+512*18,physical_M9K_packing_and_new_decode_cost_unmeasured=True),phase_alias=dict(new_RTL_tested=False,only_after_all_source_and_independent_drains=True),ports=port_rows,source_ownership=source_rows,display_gates=gates,hint908=hint,passive=dict(timeline_exact396=True,RTL_files=32,first_missed_capture=911,failure_ms=316.648557725,actualM4_IRQ_SPI_2slot_ROM_retained=True,CPU_service_is_measured_native_not_lockstep=True),required_gates=['delete old host/checker/source/plan/queue/SPI/hint bodies,not wrap them','hardwired actualread/token/CRC handshake has no perbyte context fetch','coherent pinned status bank and atomic publication before IRQ','one physical owner for each RAM port;SPI/ctx accesses cannot become a third port','new complete ROM schedule must reach908 VBlank17 and sustainedcapture911','variableEA count1..7,EA7retire distinction,STOP/drain/lateDONE,independentchecks remain tested','samefunctional/wholeRTL/newM4/newnativeABI matching before next wholeMAP/FIT'],not_proven=['new executor or variableEA functional implementation','1017/1172 comb feasibility','new actualM4 instructions/static/IRQ/2slot costs','time gain or60fps','FIT/STA/MMC4-5/fullresident/WCET/physical board'],pins=pins)
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k]for k in('audit_passed','expanded_hint_boundary','ports','display_gates','hint908')},indent=2))
if __name__=='__main__':main()
