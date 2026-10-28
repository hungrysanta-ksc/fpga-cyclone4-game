# SPDX-License-Identifier: MIT
"""Reconcile actual386CPU DMA/gather costs and unchanged375/377 joint schedule."""
import argparse,csv,json,re
from collections import defaultdict
from pathlib import Path
import analyze_nes_source368 as old
from analyze_nes_receipt335 import completed_unit,load_image
from nes_bg295 import unbatch
from probe_nes_spool383 import current_view,plans
from nes_delta231 import ROOT,BASE,sha

MASTER_MS=46561/1e9
def rows(p):return [list(map(int,x))for x in csv.reader(p.read_text().splitlines())]
def one(ev,kind,f):return old.event(ev,kind,f)

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--joint',type=Path,required=True);a=p.parse_args()
 root=BASE/'probes/nes-burst386';native=root/'native08';nr=old.js(native/'result.json');guards=old.js(root/'guards03/result.json')
 assert nr['passed'] and len(nr['cases'])==11 and guards['passed'] and len(guards['cases'])==11
 assert nr['source']==sha(ROOT/'tools/probe_nes_burst386.py')==sha(native/'probe_nes_burst386.py')
 assert guards['source']==sha(ROOT/'tools/guard_nes_burst386.py')==sha(root/'guards03/guard_nes_burst386.py')
 oracle,_=plans();table=[];pins={}
 for row in nr['cases']:
  f=row['frame'];q=native/(str(f)+('-stop'if row.get('STOP')else''))
  for fn,field in [('spool.sfc','ROM'),('events.csv','events'),('timings.csv','timings'),('fixture.json','fixture')]:assert sha(q/fn)==row[field];pins[str(q/fn)]=row[field]
  if row.get('STOP'):assert not row['final_ACK'];continue
  jobs=old.js(q/'fixture.json');ev=rows(q/'events.csv');view=current_view(f);script=(q/'capture.lua').read_text()
  prior=(oracle/f'expected-{f-906}.bin').read_bytes();expected=(oracle/f'expected-{f-904}.bin').read_bytes()
  for key,data in [('INITMAP',prior[:4096]),('INITOAM',prior[4608:5152]),('EXPECTMAP',expected[:4096]),('EXPECTOAM',expected[4608:5152])]:assert bytes.fromhex(re.search('local '+key+'="([0-9a-f]*)"',script)[1])==data
  assert bytes.fromhex((q/'current-display.hex').read_text())==view
  assert bytes(x[3]for x in ev if x[1]==0 and 0x6070<=x[2]<=0x607b)==view
  assert bytes(x[3]for x in ev if x[1]==1 and x[2] in (0x210d,0x210e))==view[8:12]
  maps=[j for j in jobs if j['typed']and bytes.fromhex(j['descriptor'])[0]&2];cols=defaultdict(set)
  for j in maps:
   desc=bytes.fromhex(j['descriptor']);first=int.from_bytes(desc[3:5],'little');n=len(bytes.fromhex(j['data']))//2
   assert first+n<=2048
   for word in range(first,first+n):cols[(word//1024,word%32)].add((word//32)%32)
  spans=[dict(screen=k[0],column=k[1],first=min(v),last=max(v))for k,v in sorted(cols.items())]
  nbytes=sum(len(bytes.fromhex(j['data']))for j in maps);cbytes=sum((x['last']-x['first']+1)*2 for x in spans)
  costs=[1280*len(maps)+8*nbytes,min(65535,1280*len(cols)+8*cbytes),34048]
  choice=0 if len(maps)<=7 and nbytes<=128 else min(range(3),key=lambda k:costs[k])
  assert row['strategy']==choice and row['sparse_cost']==min(65535,costs[0])
  if choice!=0:assert row['column_cost']==costs[1]
  data=[x for x in ev if x[1]==1 and x[2] in (0x2118,0x2119,0x2122,0x2104)]
  stored=[x for x in ev if x[1]==1 and x[2] in (0x6050,0x6059)];assert len(stored)==len(jobs)
  assert min(x[4]for x in data)>max(x[4]for x in stored)
  assert all(225<=x[5]<262 and x[4]//357368==row['ACK_master']//357368 for x in data)
  tiles=[j for j in jobs if j['typed']and not bytes.fromhex(j['descriptor'])[0]&2];tbytes=sum(len(bytes.fromhex(j['data']))for j in tiles)
  mapbytes=[nbytes,cbytes,4096][choice];assert len(data)==tbytes+mapbytes+544
  first_poll=next(x[4]for x in ev if x[1:3]==[0,0x4212]);last_view=max(x[4]for x in ev if x[1]==0 and 0x6070<=x[2]<=0x607b)
  tail=row['ACK_master']-max(x[4]for x in ev if x[1:3]==[0,0x4212]and x[4]<row['PPU_start'])
  prev=BASE/f'probes/nes-spool383/native07/{f}';pe=rows(prev/'events.csv');pr=old.js(prev/'cpu-result.json')
  oldpre=next(x[4]for x in pe if x[1:3]==[0,0x4212])-max(x[4]for x in pe if x[1]==0 and 0x6070<=x[2]<=0x607b)
  oldtail=pr['ACK_master']-max(x[4]for x in pe if x[1:3]==[0,0x4212]and x[4]<pr['PPU_start'])
  table.append(dict(frame=f,strategy=('sparse','column','dense')[choice],map_ranges=len(maps),received_map_bytes=nbytes,column_spans=spans,column_bytes=cbytes,PPU_map_bytes=mapbytes,PPU_jobs=row['PPU_jobs'],all_PPU_bytes=len(data),native_admission_cutoff_line=246 if 3328+1280*row['PPU_jobs']+8*len(data)<=20000 else 238 if 3328+1280*row['PPU_jobs']+8*len(data)<=30000 else 230 if 3328+1280*row['PPU_jobs']+8*len(data)<=40000 else 225,
   preflight_clocks=first_poll-last_view,previous_preflight_clocks=oldpre,preflight_ms=(first_poll-last_view)*MASTER_MS,tail_clocks=tail,previous_tail_clocks=oldtail,tail_ms=tail*MASTER_MS,tail_gain_ms=(oldtail-tail)*MASTER_MS,
   full_map_tile_OAM_and_current_view_checked=True,valid_prior_WRAM_and_VRAM_fixture=True))
 for row in guards['cases']:
  q=root/'guards03'/row['name'];assert sha(q/'spool.sfc')==row['ROM'] and sha(q/'events.csv')==row['events']
  ev=rows(q/'events.csv')
  if row.get('STOP_or_capacity_abort'):
   assert not row['final_ACK'] and not any(x[1:3]==[1,0x6058]for x in ev)
  else:
   data=[x for x in ev if x[1]==1 and x[2]in(0x2118,0x2119,0x2122,0x2104)]
   assert all(225<=x[5]<262 and x[4]//357368==row['ACK_master']//357368 for x in data)
 assert next(x for x in guards['cases']if x['name']=='dense')['strategy']==2
 assert next(x for x in guards['cases']if x['name']=='palette')['staged']==14
 assert next(x for x in guards['cases']if x['name']=='columnholes')['strategy']==1
 profile=[]
 for f in (907,908,915):
  q=root/f'profile01/{f}';assert sha(q/'spool.sfc')==sha(native/str(f)/'spool.sfc') and sha(q/'events.csv')==sha(native/str(f)/'events.csv')
  tm=list(csv.DictReader((q/'timings.csv').read_text().splitlines()));marks={}
  for x in tm:marks.setdefault(x['phase'],int(x['clock']))
  profile.append(dict(frame=f,first_marker_clocks=marks,ROM_and_bus_timing_identical=True))
 d=a.joint;raw=(d/'vsim.log').read_text();assert '-gROM_WINDOW=1' in raw;ev=old.events(d);manifest=old.js(d/'manifest384.json');oldjoint=BASE/'probes/nes-spool383/joint04';oe=old.events(oldjoint)
 assert (d/'joint266_tb.sv').read_bytes()==(oldjoint/'joint266_tb.sv').read_bytes();assert load_image(d/'output.elf')==load_image(oldjoint/'output.elf')
 board=BASE/'probes/nes-context375/map03';names=set(re.findall(r'-name SYSTEMVERILOG_FILE\s+"?([^\s"]+)',(board/'board.qsf').read_text()));shared={}
 for n in names:
  if(d/n).exists():assert sha(d/n)==sha(board/n);shared[n]=sha(d/n)
 assert len(shared)==31
 # Retain the identical qualifier, fixed capture deadlines and ROM priority assertion.
 qualifier="(romcycle267%357368>=330088&&romcycle267%357368<354640&&romcycle267%12==3)"
 assert qualifier in(d/'joint266_tb.sv').read_text()and qualifier in(oldjoint/'joint266_tb.sv').read_text()
 completed=[int(x[1])for x in ev if x[0]=='frame_done'];frames=[]
 for f in completed:
  assert unbatch((d/f'actual-plans293-{f}.bin').read_bytes())==unbatch((BASE/f'probes/nes-frontier377/joint01/actual-plans293-{f}.bin').read_bytes())
  expected_units=[];actual_units=[];at=0;token=None;private=[]
  for x in ev:
   if x[1]!=str(f):continue
   if x[0]=='read336':
    tok,op,section,pos,offset,value,t=map(int,x[2:]);assert offset==at
    if at==0:token=tok
    assert token==tok;at+=1;unit=completed_unit(op,section,pos,2)
    if unit:expected_units.append((tok,int(unit[0]),unit[1]))
   elif x[0]=='unit336':actual_units.append(tuple(map(int,x[2:5])))
   elif x[0]=='private336':assert int(x[2])==token;private.append(int(x[-1]))
   elif x[0]=='publish336':
    tok,n,t=map(int,x[2:]);assert tok==token and n==at and all(v<t for v in private);at=0;token=None;private=[]
  assert expected_units==actual_units and at==0
  start=one(ev,'start319',f);end=one(ev,'frame_done',f);prevstart=next((x for x in oe if x[:2]==['start319',str(f)]),None);prevend=next((x for x in oe if x[:2]==['frame_done',str(f)]),None)
  r=dict(frame=f,start_ps=int(start[2]),ROM_start_cycle=int(start[3]),done_ps=int(end[2]),processing_ms=(int(end[2])-int(start[2]))/1e9,same_start_and_ROM_cycle=start==prevstart,
   absolute_completion_gain_ms=(int(prevend[2])-int(end[2]))/1e9 if prevend else None,independent_read_units=len(actual_units))
  if f>=907:
   ready=one(ev,'display_ready378',f);present=one(ev,'present384',f);window=one(ev,'vblank384',f);stores=[x for x in ev if x[:2]==['stored384',str(f)]];ppu=[x for x in ev if x[:2]==['ppu384',str(f)]]
   assert len(stores)==next(x['source_records']for x in manifest['profiles']if x['frame']==f)
   assert max(int(x[-1])for x in stores)<min(int(x[-2])for x in ppu)
   assert all(225*1364<=int(x[-1])<357368 for x in ppu)
   cutoff=next(x['native_admission_cutoff_line']for x in table if x['frame']==f);assert int(window[3])//1364<=cutoff
   r.update(ready_ps=int(ready[2]),ready_gain_ms=(int(one(oe,'display_ready378',f)[2])-int(ready[2]))/1e9,display_poll_ps=int(one(ev,'display_poll378',f)[2]),display_poll_phase=int(one(ev,'display_poll378',f)[3]),native_admission_cutoff_line=cutoff,present_ps=int(present[2]),VBlank_index=int(present[3]),VBlank_service_ms=(int(present[2])-int(window[2]))/1e9,remaining_VBlank_ms=(357368-int(present[4]))*MASTER_MS)
  frames.append(r)
 assert next(x for x in frames if x['frame']==907)['same_start_and_ROM_cycle']
 captures=[dict(frame=int(x[1]),admitted=x[3]=='1',time_ps=int(x[5]))for x in ev if x[0]=='capture_attempt367']
 failure=re.search(r'Fatal: next capture deadline missed367 frame(\d+) owned(\d+)',raw)
 if failure:assert 'Errors: 1, Warnings: 0'in raw
 else:assert 'PASS REFILL267'in raw and 'Errors: 0, Warnings: 0'in raw
 r908=next(x for x in frames if x['frame']==908)
 post_seal_budget_clocks=r908['native_admission_cutoff_line']*1364-r908['display_poll_phase']
 # Anchor the shared ROM phase to the actual VBlank event,not wallclock zero.
 hint=one(ev,'hint_fill367',908);win=one(ev,'vblank384',908)
 hint_phase=(int(win[3])+round((int(hint[2])-int(win[2]))/46561))%357368
 assert 330088<=hint_phase<354640
 causal=dict(frame908_first_hint_fill_ps=int(hint[2]),first_hint_ROM_phase=hint_phase,first_window_close_phase=354640,hint_close_margin_ms=(354640-hint_phase)*MASTER_MS,
  previous_frame908_hint_fill_events=sum(x[:2]==['hint_fill367','908']for x in oe),post_view_to_native_cutoff_clocks=post_seal_budget_clocks,post_view_to_native_cutoff_ms=post_seal_budget_clocks*MASTER_MS,next_preflight_target_ms=0.8,
  margin_is_not_mapper_allowance=True)
 pins.update({str(d/n):sha(d/n)for n in('vsim.log','joint-events.csv','joint266_tb.sv','output.elf','manifest384.json')})
 for n in('probe_nes_burst386.py','guard_nes_burst386.py','profile_nes_burst386.py','probe_nes_burst387.py','analyze_nes_burst387.py'):pins[str(ROOT/'tools'/n)]=sha(ROOT/'tools'/n)
 report=dict(stage=387,audit_completed=True,native386=table,guards=guards,passive_CPU_profile=profile,
  causal_schedule=causal,continuous387=dict(passed=not bool(failure),completed=completed,frames=frames,captures=captures,first_missed_capture=int(failure[1])if failure else None,native_profiles=manifest,
   scope='Actual377 M4 and375 RTL;native386 observed service allocation,325WRAM ordinary and381view head retained;not fullresidentCPU/WCET.'),
  cost=dict(ROM_body_bytes=3290,prior383_ROM_body_bytes=2168,existing_board_ROM_slot_bytes=4096,new_ROM_installed_on_board=False,payload_record_SNES_WRAM_bytes=24705,prior383_payload_record_WRAM_bytes=20480,extra_SNES_WRAM_bytes=4225,extra_live_DP_bytes=30,stack_extra=None,
   shared_RTL_unchanged=shared,ARM_load_image_unchanged=True,new_FPGA_savings=0,whole_Lite_inherited375=old.whole(board),comb_deficit=2255,required_net_deletion_with155reserve=2410,new_MAP=False,FIT_STA=False),
  correction='385 column model conflated the two32x32screens. Actual386 uses(screen,column,row),128B bounds plus1B validity;old1column/80B908 estimate is superseded by2columns/32B.',
  limits=['Warm prior WRAM/VRAM/OAM and HDMA terminators are explicit fixtures;no cold initialization or postSTOP normal recovery.','Invalid-cache-bit rejection and STOP clearing both cache bits are native CPU guards;no live cache epoch/generation recovery proof.','Sparse shortcut<=7ranges/128B is a bounded policy,not a global DMA optimum. Column/dense budget is not a global CPU+SPI cost optimizer.','Independent FPGA expected/CRC/coverage proves received source storage;unseen SNES cached map/PPU bytes are not hardware-checked.','Dense/palette guard cases are synthetic output-ABI workloads,not extra ARM/NES frames.','No new FPGA area recovery,fullresidentfirmware/71heavy7/multipleROMphases/livecoremapper/WCET/fullpixels/physical60fps/MMC4-5 margin proof.'],
  hardware_sources=['https://snes.nesdev.org/wiki/PPU_registers','https://snes.nesdev.org/wiki/Scrolling_a_large_map'],physical=False,sustained60fps=False,pins=pins)
 a.out.write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps(dict(completed=completed,captures=captures,frames=frames),indent=2))
if __name__=='__main__':main()
