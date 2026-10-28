# SPDX-License-Identifier: MIT
"""Separate native383 proof,384 partial schedule,385 lifetime and burst budgets."""
import argparse,csv,json,re
from collections import defaultdict
from pathlib import Path
import analyze_nes_source368 as old
from analyze_nes_receipt335 import completed_unit,load_image
from nes_bg295 import unbatch
from nes_context375 import COMMON
from probe_nes_spool383 import current_view,plans
from nes_delta231 import ROOT,BASE,sha


def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--run',default='joint04');p.add_argument('--cancel',type=Path);a=p.parse_args();root=BASE/'probes/nes-spool383';native=root/'native07';ref=BASE/'probes/nes-frontier377/joint01';board=BASE/'probes/nes-context375/map03'
 nr=old.js(native/'result.json');assert nr['passed'] and len(nr['cases'])==11;nc=[];adaptive=[];oracle,_=plans()
 for row in nr['cases']:
  frame=row['frame'];name=str(frame)+('-stop' if row.get('STOP') else '');q=native/name
  for filename,field in [('spool.sfc','ROM'),('events.csv','events'),('timings.csv','timings'),('fixture.json','fixture')]:assert sha(q/filename)==row[field]
  if row.get('STOP'):assert not row['final_ACK'] and row['PPU_jobs']==0;continue
  jobs=old.js(q/'fixture.json');ev=[list(map(int,x)) for x in csv.reader(old.read(q/'events.csv').splitlines())]
  script=old.read(q/'capture.lua')
  prior=oracle/f'expected-{frame-906}.bin';expected_image=oracle/f'expected-{frame-904}.bin'
  for source in (prior,expected_image,BASE/f'probes/nes-present378/control02/arm{frame}.json',BASE/f'probes/nes-present378/control02/prelude{frame}.hex'):old.PINS[str(source)]=sha(source)
  for label,data in [('INITMAP',prior.read_bytes()[:4096]),('INITOAM',prior.read_bytes()[4608:5152]),('EXPECTMAP',expected_image.read_bytes()[:4096]),('EXPECTOAM',expected_image.read_bytes()[4608:5152])]:assert bytes.fromhex(re.search('local '+label+'="([0-9a-f]*)"',script)[1])==data
  view=bytes.fromhex(old.read(q/'current-display.hex'));assert view==current_view(frame)
  reads=[x for x in ev if x[1]==0 and 0x6070<=x[2]<=0x607b];assert bytes(x[3] for x in reads)==view
  staged=[x for x in ev if x[1]==1 and x[2] in (0x6050,0x6059)];assert len(staged)==len(jobs)
  data=[x for x in ev if x[1]==1 and x[2] in (0x2118,0x2119,0x2122,0x2104)]
  assert data and min(x[4] for x in data)>max(x[4] for x in staged)
  assert all(225<=x[5]<262 and x[4]//357368==row['ACK_master']//357368 for x in data)
  tiles=[j for j in jobs if j['typed'] and not bytes.fromhex(j['descriptor'])[0]&2]
  tbytes=sum(len(bytes.fromhex(j['data'])) for j in tiles);assert len(data)==tbytes+4096+544
  scroll=[x[3] for x in ev if x[1]==1 and x[2] in (0x210d,0x210e)];assert bytes(scroll)==view[8:12]
  nc.append(dict(frame=frame,source_records=len(jobs),PPU_jobs=row['PPU_jobs'],PPU_bytes=len(data),PPU_wire_only_clocks=len(data)*8,
   first_PPU_to_ACK_clocks=row['ACK_master']-row['PPU_start'],ACK_scanline=row['ACK_scanline'],actual_PPU_data_and_current_view=True,initial_target_bank_images_preloaded=True))
  maps=[j for j in jobs if j['typed'] and bytes.fromhex(j['descriptor'])[0]&2];cols=defaultdict(set)
  for j in maps:
   desc=bytes.fromhex(j['descriptor']);first=int.from_bytes(desc[3:5],'little');n=len(bytes.fromhex(j['data']))//2
   for word in range(first,first+n):cols[word%32].add(word//32)
  span=sum((max(v)-min(v)+1)*2 for v in cols.values());nbytes=sum(len(bytes.fromhex(j['data'])) for j in maps)
  costs=dict(sparse=1280*len(maps)+8*nbytes,dense=1280+8*4096,column=1280*len(cols)+8*span)
  adaptive.append(dict(frame=frame,original_map_records=len(maps),original_map_bytes=nbytes,column_spans=[dict(column=k,first=min(v),last=max(v)) for k,v in sorted(cols.items())],column_span_bytes=span,
   modeled_map_clocks=costs,modeled_choice=min(costs,key=costs.get),native_implemented=False,gather_cost_clocks=None,extra_SNES_RAM_budget_bytes=4176,actual_time_gain_ms=None))
 guards=old.js(root/'guards04/result.json');assert guards['passed'] and len(guards['cases'])==7
 for row in guards['cases']:
  d=root/'guards04'/row['name'];assert sha(d/'spool.sfc')==row['ROM'] and sha(d/'events.csv')==row['events']
 assert next(x for x in guards['cases'] if x['name']=='densepalettebudget')['PPU_jobs']==0
 d=root/a.run;raw=old.read(d/'vsim.log');ev=old.events(d);manifest=old.js(d/'manifest384.json')
 assert 'Fatal: next capture deadline missed367 frame911 owned1 initialized1 release0 fault0' in raw
 assert 'Errors: 1, Warnings: 0' in raw and 'native scroll/view mismatch384' in old.read(d/'joint266_tb.sv')
 assert load_image(d/'output.elf')==load_image(ref/'output.elf')
 for elf in (d/'output.elf',ref/'output.elf'):old.PINS[str(elf)]=sha(elf)
 board_names=set(re.findall(r'-name SYSTEMVERILOG_FILE\s+"?([^\s"]+)',old.read(board/'board.qsf')));shared={}
 for n in board_names:
  if (d/n).exists():assert sha(d/n)==sha(board/n);shared[n]=sha(d/n)
 assert len(shared)==31
 completed=[int(x[1]) for x in ev if x[0]=='frame_done'];assert completed==[905,906,907,908]
 frames=[]
 for f in completed:
  actual=d/f'actual-plans293-{f}.bin';assert unbatch(actual.read_bytes())==unbatch((ref/actual.name).read_bytes())
  for source in (actual,ref/actual.name):old.PINS[str(source)]=sha(source)
  expected=[];observed=[];at=0;token=None;private=[];published=0
  for x in ev:
   if x[1]!=str(f):continue
   if x[0]=='read336':
    tok,op,section,pos,offset,value,t=map(int,x[2:]);assert offset==at
    if not at:token=tok
    assert tok==token;at+=1;unit=completed_unit(op,section,pos,2)
    if unit:expected.append((tok,int(unit[0]),unit[1]))
   elif x[0]=='unit336':observed.append(tuple(map(int,x[2:5])))
   elif x[0]=='private336':assert int(x[2])==token;private.append(int(x[-1]))
   elif x[0]=='publish336':
    tok,n,t=map(int,x[2:]);assert tok==token and n==at and all(p<t for p in private);at=0;token=None;private=[];published+=1
  assert expected==observed and not at
  start=old.event(ev,'start319',f);end=old.event(ev,'frame_done',f);row=dict(frame=f,start_ps=int(start[2]),ROM_start_cycle=int(start[3]),processing_ms=(int(end[2])-int(start[2]))/1e9,qualified_units=len(observed),published=published,semantic_plan_exact377=True)
  if f>=907:
   ready=old.event(ev,'display_ready378',f);present=old.event(ev,'present384',f);window=old.event(ev,'vblank384',f);stores=[x for x in ev if x[:2]==['stored384',str(f)]];ppu=[x for x in ev if x[:2]==['ppu384',str(f)]]
   assert len(stores)==next(p['source_records'] for p in manifest['profiles'] if p['frame']==f)
   assert max(int(x[-1]) for x in stores)<min(int(x[-2]) for x in ppu)
   assert all(225*1364<=int(x[-1])<357368 for x in ppu)
   row.update(display_ready_ps=int(ready[2]),display_ready_ms=(int(ready[2])-int(start[2]))/1e9,ACK_ps=int(present[2]),VBlank_index=int(present[3]),VBlank_service_ms=(int(present[2])-int(window[2]))/1e9,remaining_VBlank_ms=(357368-int(present[4]))*46561/1e9,stored_records=len(stores),PPU_port_writes=len(ppu),current_scroll_checked=True)
  frames.append(row)
 captures=[dict(frame=int(x[1]),owned=int(x[2]),admitted=x[3]=='1',time_ps=int(x[5])) for x in ev if x[0]=='capture_attempt367'];assert [x['admitted'] for x in captures]==[True,True,True,False]
 before=old.js(ROOT/'analysis/present378-verification.json')['runs']['commit382-01'];br=before['display_ready'][0];new=next(x for x in frames if x['frame']==907)
 assert old.event(ev,'start319',907)[2:]==old.event(old.events(BASE/'probes/nes-present378/commit382-01'),'start319',907)[2:]
 previous=old.events(root/'joint03')
 for f in completed:
  assert old.event(ev,'start319',f)==old.event(previous,'start319',f)
  assert old.event(ev,'frame_done',f)==old.event(previous,'frame_done',f)
 for f in (907,908):assert old.event(ev,'present384',f)==old.event(previous,'present384',f)
 sink=board/'nes_sink_bus165.sv';assert 'program_rom[0:4095]' in old.read(sink)
 armrows=[json.loads(line) for line in old.read(d/'arm-worker.log').splitlines() if line.startswith('{')];assert [r['frame'] for r in armrows]==completed
 arm=dict(completed_frames=[dict(frame=r['frame'],instructions=r['instructions'],SPI_bytes=r['SPI_bytes'],source_instructions=r['source_instructions367']) for r in armrows],final_stack_observation=None,full_RUN=False,physical_cycles=False)
 ingest=old.js(root/'ingest03/result.json');assert ingest['audit_completed'] and ingest['counterexample']['incorrect_published_display_serial']==4
 publication=old.js(root/'publish03/result.json');assert publication['passed'] and len(publication['cases'])==16 and publication['extra_static_RAM_bytes']==0
 assert publication['cases'][0]['observed_component_stack_bytes']==20
 assert sha(root/'publish03/unit.elf')==publication['pins'][str(Path('C:/Users/mohallo/AppData/Local/Temp/nes-spool383/publish03/unit.elf'))]
 cancel=old.js(a.cancel/'result.json') if a.cancel else None
 if cancel:assert cancel['passed'] and cancel['all_source_staged_before_STOP'] and cancel['view_reads']==36 and cancel['RAM_frozen_host_clocks']==256 and not cancel['final_ACK']
 failures={}
 for tag,logfile in [('native01','../nes-spool383-native01.log'),('native02','../nes-spool383-native02.log'),('native03','../nes-spool383-native03.log'),('joint01','joint01.log'),('joint02','joint02.log'),('cancel01','cancel01.log'),('guards02','guards02.log'),('guards03','guards03.log'),('ingest01','ingest01.log')]:
  path=root/logfile
  if path.exists():failures[tag]=dict(raw_log_SHA256=sha(path),passed=False)
 for name in ('probe_nes_spool383.py','probe_nes_spool384.py','guard_nes_spool383.py','guard_nes_spool384.py','audit_nes_ingest385.py','analyze_nes_spool385.py','nes_publish385.c','check_nes_publish385.py'):old.PINS[str(ROOT/'tools'/name)]=sha(ROOT/'tools'/name)
 report=dict(stage=385,audit_completed=True,native383=nc,native_guards=guards,continuous384=dict(passed=False,completed=completed,frames=frames,captures=captures,ARM=arm,profiles=manifest,PPU_destination_proof='Native383 fixture;whole384 is service replay with live source reads,not fullresidentCPU execution'),
  first907_display_ready_gain_ms=(br['time_ps']-new['display_ready_ps'])/1e9,previous_first_missed_capture=910,first_missed_capture=911,capture_deferred_not_solved=True,shared_board_RTL=shared,whole_MAP=dict(inherited375=True,new_MAP=False,after=old.whole(board)),comb_deficit=2255,required_net_deletion_with155reserve=2410,
  SNES_candidate=dict(ROM_body_bytes=2168,existing_board_ROM_bytes=4096,combined_firmware_ROM_bytes=None,board_ROM_program_updated=False,WRAM_bytes=20480,tile_spool='7E8000..7E9FFF',records='7EA000..7EAFFF',bank_maps='7EC000..7EDFFF',complete_firmware_RAM_admission=False,cold_bank_initialization=False,STOP_recovery=False),
  current_view_binding_fix_changed_timing=False,
  ingest385=ingest,publication385_component=publication,adaptive_burst_budget=adaptive,cancel=cancel,preserved_failures=failures,
  next='Compare adaptive sparse/column/dense SNES bursts with actual preflight/gather cost before widening ARM/FPGA hint ownership. Publication component reusescurrentmetadata with0newstatic/20stack;RX24B isstillabudget. Frozen16B+RX24B40B remainsanalternative,notaschedulerimplementation.',
  limits=['375RTL/377ARM unchanged;no FPGA saving/fullFITSTA/physical60fps.','Native prior-bank WRAM state and HDMA terminators are explicitfixtures,not coldboot/fullpixel proof;CGRAM-only guard also preloads priorVRAM/OAM.','Source receipt proves WRAM storage,not PPU completion;nativeCPU control delays finalACK. FPGA independently checks source CRC/coverage,not unseen SNESWRAM cachedwords.','384 has mixed383 typed/PPU service,325ordinaryWRAMservice and381head allocations;not one compiledfullresidentconsumer.','Standalone383 startup writes4201/420c/2100 are not a production per-frame setup;WRIOshadow/HDMA/liveIO/frame-resetcost need integration.','Native timing includes modeledMesenrefresh;recorded profiles and one relativephase are not generalWCET.','Warmdisplay sample ismask0x18/raw2;othermask/rawcount branches needseparateproof.','CGRAMonly CPU case passes;densepalettebudget isasynthetic output-ABI size/type case,notanadditional ARM/NES-produced frame;it abortsbeforePPU andneedsfallback.','Initialjoint03usedoldfixture scroll view;finaljoint04 bindsactualcurrentview andmustbeused forfunctionalresults.','EarlyARMsource changes currentreceiver/history;publish352 and hintgeneration ownership need jointreplacement before enabling it.'],
  hardware_sources=['https://snes.nesdev.org/wiki/Timing','https://snes.nesdev.org/wiki/PPU_registers'],physical=False,sustained60fps=False,pins=old.PINS)
 a.out.write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps(dict(audit_completed=True,native_cases=len(nc),native_guards=len(guards['cases']),completed=completed,captures=captures,ready_gain_ms=report['first907_display_ready_gain_ms'],warm=[x for x in frames if x['frame']>=907]),indent=2))
if __name__=='__main__':main()
