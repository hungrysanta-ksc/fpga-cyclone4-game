# SPDX-License-Identifier: MIT
"""Bind actual390 M4 plans,391CPU and392 live schedule to whole Lite costs."""
import argparse,csv,json,re,hashlib
from collections import defaultdict
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
import analyze_nes_source368 as audit
from analyze_nes_increment389 import frame as native_frame
from analyze_nes_receipt335 import completed_unit
from nes_bg295 import unbatch

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--joint',required=True,type=Path);a=p.parse_args();base=BASE/'probes/nes-plan390';d=a.joint.resolve();pins={}
 def pin(q):
  key=q.relative_to(BASE).as_posix()if q.is_relative_to(BASE)else q.name;pins[key]=sha(q);return pins[key]
 def js(q):pin(q);return json.loads(q.read_text())
 arm=js(base/'arm01/result.json');ag=js(base/'armguards01/result.json');nr=js(base/'native01/result.json');ng=js(base/'guards02/result.json');rg=js(base/'rtlguards01/result.json')
 assert arm['passed']and len(arm['cases'])==10 and ag['passed']and len(ag['cases'])==30 and ng['passed']and len(ng['cases'])==19 and rg['passed']and rg['decision_checks']==518
 assert arm['source']==pin(ROOT/'tools/nes_compact390.c')and nr['source']==pin(ROOT/'tools/probe_nes_plan391.py')
 native=[]
 for row in nr['cases']:
  f=row['frame'];q=base/'native01'/(str(f)+('-stop'if row.get('STOP')else''))
  for fn,k in [('spool.sfc','ROM'),('events.csv','events'),('timings.csv','timings'),('fixture.json','fixture')]:assert pin(q/fn)==row[k]
  if row.get('STOP'):assert not row['final_ACK'];continue
  now,ev,jobs,cpu=native_frame(q);before,_,_,_=native_frame(BASE/f'probes/nes-increment388/native07/{f}')
  parts=defaultdict(lambda:dict(records=0,bytes=0,control_clocks=0))
  for j,clocks in zip(jobs,now['control_clocks']):
   desc=bytes.fromhex(j['descriptor']);kind='map'if j['typed']and desc[0]&2 else'tile'if j['typed']else'section'+str(desc[1]);r=parts[kind];r['records']+=1;r['bytes']+=len(bytes.fromhex(j['data']));r['control_clocks']+=clocks
  stores=[e for e in ev if e[1]==1 and e[2]in(0x6050,0x6059)];pp=[e for e in ev if e[1]==1 and e[2]in(0x2118,0x2119,0x2122,0x2104)]
  assert len(stores)==len(jobs)and max(e[4]for e in stores)<min(e[4]for e in pp)
  assert all(225<=e[5]<262 and e[4]//357368==cpu['ACK_master']//357368 for e in pp)
  plan=(base/'arm01'/f'plan{f}.bin').read_bytes();assert [bytes.fromhex(j['data'])for j in jobs if not j['typed']and bytes.fromhex(j['descriptor'])[1]==6]==[plan]
  pin(base/'arm01'/f'plan{f}.bin');native.append(dict(frame=f,mode=plan[3],plan_bytes=len(plan),plan_wire_bytes=len(plan)+19,PPU_jobs=cpu['PPU_jobs'],PPU_bytes=len(pp),current=now,reference388=before,source_parts=dict(parts)))
 for case in ng['cases']:
  row=case['result'];q=base/'guards02'/case['name']/(str(row['frame'])+('-stop'if row.get('STOP')else''));pin(q/'events.csv')
  if row.get('STOP'):
   ev=[list(map(int,x))for x in csv.reader((q/'events.csv').read_text().splitlines())];writes={e[2]:e[3]for e in ev if e[1]==1};assert writes[0x2100]==128 and writes[0x420c]==0 and not any(e[1:3]==[1,0x6058]for e in ev)
 raw=(d/'vsim.log').read_text();pin(d/'vsim.log');ev=audit.events(d);pin(d/'joint-events.csv');fail=re.search(r'Fatal: next capture deadline missed367 frame(\d+) owned(\d+)',raw)
 assert fail or 'PASS REFILL267'in raw,raw[-1500:]
 assert 'Errors: 1, Warnings: 0'in raw if fail else'Errors: 0, Warnings: 0'in raw
 tb=(d/'joint266_tb.sv').read_text()
 assert '-gROM_WINDOW=1'in raw and 'while(romcycle267<5371247)'in tb and 'MASTER_PERIOD_PS378=46561,SNES_PHASE378=0'in tb
 m=js(d/'manifest384.json');meta=js(d/'manifest392.json');assert meta['native_result']==sha(base/'native01/result.json')
 rows=[];paired=[];ref=BASE/'probes/nes-increment388/joint01';old_ev=audit.events(ref)
 def worker_rows(q):return [json.loads(line)for line in(q/'arm-worker.log').read_text().splitlines()if line.startswith('{')]
 workers=worker_rows(d);old_workers=worker_rows(ref)
 def rpc_cost(q,wr):
  costs={r['frame']:dict(requests=0,charged_instruction_cycles=0,exception_cycles=0,WFI_requests=0)for r in wr};index=0;digest=hashlib.sha256()
  for file in sorted(q.glob('arm-req*'),key=lambda p:int(p.name[7:])):
   seq=int(file.name[7:]);reply=q/f'arm-rsp{seq}'
   if not reply.exists():break
   low,high,level=map(int,reply.read_text().splitlines()[0].split());time=low+(high<<32)
   while index<len(wr)and time>wr[index]['last_RTL_ns']:index+=1
   if index==len(wr):break
   n,instructions,extra=map(int,file.read_text().splitlines()[0].split());r=costs[wr[index]['frame']];r['requests']+=1;r['charged_instruction_cycles']+=instructions;r['exception_cycles']+=extra;r['WFI_requests']+=n==260
   digest.update(str(seq).encode()+b'\n'+file.read_bytes()+b'\n'+reply.read_bytes())
  return costs,digest.hexdigest()
 rpc,request_hash=rpc_cost(d,workers);old_rpc,old_request_hash=rpc_cost(ref,old_workers)
 for f in [int(e[1])for e in ev if e[0]=='frame_done']:
  start=audit.event(ev,'start319',f);done=audit.event(ev,'frame_done',f);row=dict(frame=f,start_ps=int(start[2]),ROM_start_cycle=int(start[3]),done_ps=int(done[2]),processing_ms=(int(done[2])-int(start[2]))/1e9)
  assert unbatch((d/f'actual-plans293-{f}.bin').read_bytes())==unbatch((ref/f'actual-plans293-{f}.bin').read_bytes())
  expected=[];seen=[];at=0;tok=None
  for e in ev:
   if e[1]!=str(f):continue
   if e[0]=='read336':
    token,op,section,pos,off,value,time=map(int,e[2:]);assert off==at
    if not at:tok=token
    assert token==tok;at+=1;unit=completed_unit(op,section,pos,2)
    if unit:expected.append((tok,int(unit[0]),unit[1]))
   elif e[0]=='unit336':seen.append(tuple(map(int,e[2:5])))
   elif e[0]=='publish336':assert int(e[2])==tok and int(e[3])==at;at=0;tok=None
  assert expected==seen and not at;row['qualified_units']=len(seen)
  tr=js(d/f'arm{f}.json')['transfers'];prev=js(ref/f'arm{f}.json')['transfers'];plans=[bytes.fromhex(t['tx'])for t in tr if t['tx'].startswith('e10206')]
  if f>=907:
   assert len(plans)==1 and plans[0][17:-2]==(base/'arm01'/f'plan{f}.bin').read_bytes()
   ready=audit.event(ev,'display_ready378',f);window=audit.event(ev,'vblank384',f);present=audit.event(ev,'present384',f)
   poll=audit.event(ev,'display_poll378',f);row.update(ready_ps=int(ready[2]),post_view_phase=int(poll[3]),VBlank_index=int(present[3]),VBlank_service_ms=(int(present[2])-int(window[2]))/1e9)
   oldstart=audit.event(old_ev,'start319',f);olddone=audit.event(old_ev,'frame_done',f);oldready=audit.event(old_ev,'display_ready378',f)
   paired.append(dict(frame=f,same_start_and_ROM=(start[2:4]==oldstart[2:4]),completion_gain_ms=(int(olddone[2])-row['done_ps'])/1e9,ready_gain_ms=(int(oldready[2])-row['ready_ps'])/1e9))
  w=next(r for r in workers if r['frame']==f);ow=next(r for r in old_workers if r['frame']==f)
  row.update(SPI_prefix_before_finish=sum(len(t['tx'])//2 for t in tr),SPI_bytes=w['SPI_bytes'],SPI_byte_delta=w['SPI_bytes']-ow['SPI_bytes'],extra_plan_wire_bytes=sum(len(p)for p in plans),status_E0_reads=w['status_reads'],status_E0_delta=w['status_reads']-ow['status_reads'],E2_delta=sum(t['tx'].startswith('e2')for t in tr)-sum(t['tx'].startswith('e2')for t in prev),ARM_instructions=w['instructions'],ARM_instruction_delta=w['instructions']-ow['instructions'],charged_RPC=rpc[f],reference_charged_RPC=old_rpc[f]);rows.append(row)
 assert next(r for r in paired if r['frame']==907)['same_start_and_ROM']
 board=base/'map01';assert rg['materialized_RTL']==sha(board/'nes_mux260.sv')==sha(d/'nes_mux260.sv');shared={}
 for name in re.findall(r'-name SYSTEMVERILOG_FILE\s+"?([^\s"]+)',(board/'board.qsf').read_text()):
  if(d/name).exists():assert sha(d/name)==sha(board/name);shared[name]=pin(d/name)
 assert len(shared)==31
 whole=audit.whole(board);previous=audit.whole(BASE/'probes/nes-context375/map03');delta={k:whole[k]-previous[k]for k in whole};assert delta==dict(LE=81,comb=81,FF=0,RAM_bits=0)
 def size(q):return dict(zip(('text','data','BSS'),map(int,q.read_text().splitlines()[1].split()[:3])))
 size_now=size(d/'size368.log');size_old=size(ref/'size368.log');size_delta={k:size_now[k]-size_old[k]for k in size_now}
 for name in ('output.elf','joint266_tb.sv','size368.log','manifest392.json','observed-stack390.json'):pin(d/name)
 worker=[{k:r[k]for k in('frame','instructions','packets','SPI_bytes','status_reads','early_refills')}for r in workers]
 for prof in m['profiles']:
  r=next(r for r in native if r['frame']==prof['frame']);assert r['current']['control_clocks']==prof['per_record_control_clocks']
 inflight=[]
 for f in range(907,917):
  if any(r['frame']==f for r in rows)or not(d/f'arm{f}.json').exists():continue
  tr=js(d/f'arm{f}.json')['transfers'];plans=[bytes.fromhex(t['tx'])for t in tr if t['tx'].startswith('e10206')]
  assert len(plans)==1 and plans[0][17:-2]==(base/'arm01'/f'plan{f}.bin').read_bytes()
  r=dict(frame=f,completed=False,SPI_bytes=sum(len(t['tx'])//2 for t in tr),extra_plan_wire_bytes=len(plans[0]),status_E0_reads=sum(t['tx'].startswith('e0')for t in tr))
  ready=next((e for e in ev if e[:2]==['display_ready378',str(f)]),None)
  if ready:r['ready_ps']=int(ready[2])
  inflight.append(r)
 for q in sorted(ROOT.glob('tools/*390*'))+sorted(ROOT.glob('tools/*391*'))+sorted(ROOT.glob('tools/*392*')):
  if q.is_file():pin(q)
 report=dict(stage=392,audit_completed=True,selected_for_production=False,selected_as_time_improvement=False,component_ARM=arm,ARM_guards=ag,native=native,native_guards=ng,RTL_decision_guards=rg,
  continuous=dict(passed=not bool(fail),first_missed_capture=int(fail[1])if fail else None,completed=[r['frame']for r in rows],frames=rows,inflight=inflight,ARM_worker=worker,storage_credit_peak=max(int(e[2])for e in ev if e[0]=='credits'),observed_stack=js(d/'observed-stack390.json'),captures=[e for e in ev if e[0]=='capture_attempt367']),paired=paired,
  cost=dict(ARM=size_now,ARM_delta=size_delta,SNES_ROM_body_bytes=3543,SNES_ROM_delta_vs388=269,SNES_active_fragment_WRAM_bytes=23697,SNES_both_plan_banks_reserved_WRAM_bytes=23841,SNES_reserved_delta_vs388=-928,DP_additional_conservative_bytes=52,
   whole_RTL_MAP=whole,whole_RTL_delta=delta,comb_shortfall=2336,net_deletion_with155reserve=2491,board_program_ROM_unchanged=True,resident_CPU_ROM_decode_delta=None,FIT=False,STA=False),shared_board_RTL=shared,
  scope='Real M4 producer, exact extra SPI plan and measured real65816 storage/PPU service on liveRTL;not fullresident CPU lockstep/physical/WCET. Cold905906 original. Original independent expected/CRC/coverage retained;metadata execution coverage additionally checked by native CPU.',
  charged_RPC_prefix_hash=request_hash,reference_RPC_prefix_hash=old_request_hash,
  decision='Current bound-plan adapter adds ingress and leaves legacy host/source/queue/plan control. Not simultaneous time/area success. Do not relax capture deadline, ROM phase, VBlank cutoff or512clock reserve.',pins=pins)
 a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',newline='\n');print(json.dumps(dict(continuous=report['continuous']['first_missed_capture'],frames=rows,paired=paired,cost=report['cost']),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
