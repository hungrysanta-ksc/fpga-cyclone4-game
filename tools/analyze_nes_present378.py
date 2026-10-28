# SPDX-License-Identifier: MIT
"""Separate shared-clock calibration,display service and PPU DMA-window constraints."""
import argparse,csv,json,re
from pathlib import Path
import analyze_nes_source368 as old
from analyze_nes_receipt335 import load_image,completed_unit
from nes_context375 import COMMON
from nes_delta231 import ROOT,BASE,sha
from nes_bg295 import unbatch

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--cancel',type=Path);a=p.parse_args();root=BASE/'probes/nes-present378';ref=BASE/'probes/nes-frontier377/joint01';board=BASE/'probes/nes-context375/map03'
 kernel=old.js(root/'kernel01/result.json');assert kernel['passed'] and len(kernel['cases'])==2
 for x in kernel['cases']:
  assert sha(root/f"kernel01/bank{x['bank']}/display.sfc")==x['ROM'] and x['post_view_to_first_4212_clocks']==122
  assert sha(root/f"kernel01/bank{x['bank']}/events.csv")==x['events']
 old_report=old.js(ROOT/'analysis/frontier377-verification.json');reports={};comparisons={}
 for name in ('control02','present02','present03','dma01','commit382-01'):
  d=root/name;raw=old.read(d/'vsim.log');events=old.events(d);mode=old.js(d/'manifest378.json');passed=(d/'result.json').exists() and old.js(d/'result.json').get('passed',False)
  for n in COMMON:assert sha(d/n)==sha(board/n)
  # Check every compiled production input that also occurs in the board MAP.
  compiled=list(dict.fromkeys(old.js(d/'manifest367.json')['sources']+list(COMMON)));board_names=set(re.findall(r'-name SYSTEMVERILOG_FILE\s+"?([^\s"]+)',old.read(board/'board.qsf')))
  shared={n:sha(d/n) for n in compiled if n in board_names}
  for n,h in shared.items():assert h==sha(board/n)
  materialized={n:sha(d/n) for n in board_names if (d/n).exists()}
  for n,h in materialized.items():assert h==sha(board/n)
  assert len(shared)==30 and len(materialized)==31
  assert load_image(d/'output.elf')==load_image(ref/'output.elf')
  completed=[int(x[1]) for x in events if x[0]=='frame_done'];presented=[x for x in events if x[0]=='present378'];captures=[x for x in events if x[0]=='capture_attempt367'];full=old.measure(d,916,0) if passed else None
  rows=[]
  for f in completed:
   start=old.event(events,'start319',f);end=old.event(events,'frame_done',f);plan=d/f'actual-plans293-{f}.bin';old.PINS[str(plan)]=sha(plan)
   assert unbatch(plan.read_bytes())==unbatch((ref/plan.name).read_bytes())
   expected=[];actual=[];offset=0;token=None;writes=[];published=0
   for x in events:
    if x[1]!=str(f):continue
    if x[0]=='read336':
     tok,op,section,pos,off,value,t=map(int,x[2:]);assert off==offset
     if not offset:token=tok
     assert tok==token;offset+=1;unit=completed_unit(op,section,pos,2)
     if unit:expected.append((tok,int(unit[0]),unit[1]))
    elif x[0]=='unit336':actual.append(tuple(map(int,x[2:5])))
    elif x[0]=='private336':assert int(x[2])==token;writes.append(int(x[-1]))
    elif x[0]=='publish336':
     tok,n,t=map(int,x[2:]);assert tok==token and n==offset and n>0 and all(v<t for v in writes);offset=0;token=None;writes=[];published+=1
   assert expected==actual and not offset
   rows.append(dict(frame=f,start_ps=int(start[2]),start_cycle=int(start[3]),processing_ms=(int(end[2])-int(start[2]))/1e9,qualified_units=len(actual),published=published,semantic_plan_exact377=True))
  pres=[]
  for x in presented:
   f=int(x[1]);ready=old.event(events,'display_ready378',f);poll=old.event(events,'display_poll378',f);vb=old.event(events,'vblank378',f)
   writes=[r for r in events if r[:2]==['ppu378',str(f)]];assert writes and all(int(r[-1])>=225*1364 for r in writes)
   assert int(x[-1])>=225*1364
   pres.append(dict(frame=f,ready_ps=int(ready[2]),poll_ps=int(poll[2]),VBlank_index=int(x[3]),ACK_ps=int(x[2]),
    ready_to_ACK_ms=(int(x[2])-int(ready[2]))/1e9,wait_from_poll_ms=(int(vb[2])-int(poll[2]))/1e9,PPU_writes=len(writes),PPU_writes_in_VBlank=True))
  intervals=[dict(frame=y['frame'],VBlank_steps=y['VBlank_index']-x['VBlank_index'],ACK_interval_ms=(y['ACK_ps']-x['ACK_ps'])/1e9) for x,y in zip(pres,pres[1:])]
  waits=[x for x in events if x[0]=='dma_wait379'];descs=[x for x in events if x[0]=='descriptor379']
  # Entry uses $realtime while exit uses rounded $time(ns). Preserve raw
  # timestamps and allow only that sub-ns quantization in a zero wait.
  assert all(int(x[5])-int(x[4])>=-500 for x in waits)
  dma_ends=[x for x in events if x[0]=='dma_end379' and int(x[1])>=907]
  assert all(225*1364<=int(x[-1])<357368 for x in dma_ends)
  ready=[dict(frame=int(x[1]),time_ps=int(x[2]),phase=int(x[3]),scanline=int(x[3])//1364) for x in events if x[0]=='display_ready378']
  polls=[dict(frame=int(x[1]),time_ps=int(x[2]),phase=int(x[3]),scanline=int(x[3])//1364) for x in events if x[0]=='display_poll378']
  reports[name]=dict(passed=bool(passed),mode=mode,completed_frames=completed,rows=rows,presentations=pres,presentation_intervals=intervals,
   compiled_RTL_matching_board=shared,materialized_board_RTL_matching=materialized,display_ready=ready,display_poll=polls,sameblank_events=[x for x in events if x[0]=='sameblank382'],
   captures=[dict(frame=int(x[1]),owned=int(x[2]),admitted=x[3]=='1',at_ps=int(x[5])) for x in captures],
   failures=re.findall(r'^.*(?:Fatal:|Error:).*$' ,raw,re.M),full_measure=full,
   DMA_waits=[dict(frame=int(x[1]),kind=int(x[2]),bytes=int(x[3]),wait_ms=max(0,int(x[5])-int(x[4]))/1e9,raw_entry_ps=int(x[4]),raw_exit_ps=int(x[5]),exit_time_quantized_ps=1000,entry_phase=int(x[6]),admitted_phase=int(x[7])) for x in waits],
   external_descriptor_reads=len(descs),warm_PPU_commands_completed=len(dma_ends),PPU_command_end_windows_checked=True,atomic_frame_proven=False,raw_log_sha256=sha(d/'vsim.log'))
  if name in ('dma01','commit382-01'):assert old.js(d/'manifest379.json')['warm_PPU_access_gate']
  if name=='commit382-01':reports[name]['sameblank_service']=old.js(d/'manifest382.json')
  if passed:
   comparisons[name]=[dict(frame=x['frame'],before_377_ms=y['processing_ms'],after_ms=x['processing_ms'],delta_ms=x['processing_ms']-y['processing_ms'],same_ROM_cycle=x['start_ROM_cycle']==y['start_ROM_cycle'],same_start_time=x['start_ps']==y['start_ps']) for x,y in zip(full['rows'],old_report['candidate']['rows'])]
 assert reports['control02']['passed']
 assert any('startup missed fixed capture368' in x for x in reports['present02']['failures'])
 assert reports['present03']['passed'] and max(x['VBlank_steps'] for x in reports['present03']['presentation_intervals'])==2
 for name in ('dma01','commit382-01'):
  assert not reports[name]['passed'] and any('next capture deadline missed367 frame910 owned1' in x for x in reports[name]['failures'])
  assert reports[name]['captures'][-1]['frame']==910 and not reports[name]['captures'][-1]['admitted']
 # The CPU prototype cannot improve a display deadline that is already late
 # before display application. The legal-DMA schedule reaches its first4212
 # at line260,after the predeclared current-blank cutoff257.
 assert reports['commit382-01']['display_poll'][0]['scanline']>257
 native={}
 for name,count in (('commit01',7),('vblank01',12)):
  proof=old.js(root/name/'result.json');assert proof['passed'] and len(proof['cases'])==count
  for row in proof['cases']:
   d=root/name/row['name'];assert sha(d/'display.sfc')==row['ROM'] and sha(d/'events.csv')==row['events']
  native[name]=proof
 capsule=old.js(root/'vblank01/capsule/result.json')
 for row in capsule['cases']:
  d=root/'vblank01/capsule'/f"bank{row['bank']}";assert sha(d/'display.sfc')==row['ROM'] and sha(d/'events.csv')==row['events']
  for kind in ('head','tail'):
   original=Path(row[f'derived_{kind}']);path=root/'vblank01'/original.parent.name/original.name
   assert sha(path)==row[f'derived_{kind}_SHA']
 # Payload bandwidth bound is distinct from serialized per-command policy.
 timing=list(csv.DictReader(old.read(ref/'CPU-timing.csv').splitlines()));events=old.events(ref);payload=[]
 for row in old_report['candidate']['rows'][2:]:
  f=row['frame'];dma=int(old.event(events,'consumer',f)[-1]);oam=sum(int(x['output_bytes']) for x in timing if int(x['serial'])==f-904 and int(x['section']) in (3,4))
  payload.append(dict(frame=f,tile_map_bytes=dma,CGRAM_OAM_bytes=oam,PPU_wire_only_ms=(dma+oam)*8*46561/1e9,includes_setup_or_IRQ=False))
 cancel=old.js(a.cancel/'result.json') if a.cancel else None
 if cancel:
  assert cancel['passed'] and cancel['view_reads']==12 and cancel['PPU_writes']==0 and not cancel['final_ACK']
  for n,h in cancel['RTL'].items():assert sha(board/n)==h
 compile_failures={}
 for name,marker in (('control01','MASTER_PERIOD_PS378'),('cancel01','endelse')):
  path=root/name/'vlog.log';raw=old.read(path);assert 'Errors: 2, Warnings: 0' in raw and marker in raw
  compile_failures[name]=dict(passed=False,errors=re.findall(r'^\*\* Error:.*$',raw,re.M),log_sha256=sha(path))
 worker=root/'commit382-01/executed-worker367.py';source=old.read(worker)
 ingest=source.index("arm.call('source_receive367'");finish=source.index("call('finish267')");commit=source.index("call('commit285')")
 assert ingest<finish<commit
 serialization=dict(source=str(worker),SHA256=sha(worker),call_order=['source_receive367','plan/transmit','finish267','commit285'],next_frame_source_before_display_retire=False,additional_frozen_context_RAM_bytes=None)
 for suffix in ('378','379','380','381','382'):
  for f in ROOT.joinpath('tools').glob('*'+suffix+'*'):old.PINS[str(f)]=sha(f)
 result=dict(stage=378,audit_completed=True,kernel=kernel,native_CPU=native,derived_capsule381=capsule,runs=reports,comparison_to_377=comparisons,compile_failures=compile_failures,ARM_serialization=serialization,
  master_period_ps=46561,SNES_phase_cycles=0,frame_period_ms=357368*46561/1e9,VBlank_window_ms=50468*46561/1e9,
  warm_payload_bounds=payload,cancel=cancel,whole_MAP=dict(inherited375=True,new_MAP=False,after=old.whole(board)),comb_deficit=2255,required_with155reserve=2410,
  boot_coupled_passed=False,full_CPU=False,live_mapper=False,FIT=False,STA=False,physical=False,sustained60fps=False,
  limits=['378 actual415B code and380/381 actual472/516B prototypes use mocked view/status/token and explicitzeroHDMAterminators;not full production resident CPU/HDMA upload.','Display timing is trace-service replay at shared SYSCLK and one predeclared relative PPU phase,not measured hardware phase/WCET.','Control/cold display failure/warm-only display/whole-command warm PPU gate are distinct scopes.','379 gates wholeCGRAM/OAM commands including WRAM copy;failure is not an optimal-schedule impossibility proof.','382 derives early head/currentblank tail from native381 traces;extra counter cost is charged conservatively on nextblank paths. Not arbitraryphaseCPU reexecution.','381 counter latch requiresWRIO.7 enabled;production must preserve/establishtheoutputshadow.','PPU access-window compliance alone does not prove palette/OAM atomicity or final pixels.','Source/ARM/ROM/heavy71,multiple phases/fullCPU/FITSTA/physical admission remain open.'],
  sources=[dict(url='https://snes.nesdev.org/wiki/PPU_registers',claim='VRAM writes require VBlank or forcedblank;inactive destination bank does not change availability.'),dict(url='https://snes.nesdev.org/wiki/Reading_and_writing_PPU_memory',claim='PPU transfer constraints andDMA destinations.')],pins=old.PINS)
 a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',newline='\n');print(json.dumps(dict(audit_completed=True,runs={n:dict(passed=x['passed'],completed=x['completed_frames'],captures=x['captures'],presentations=x['presentation_intervals'],failures=x['failures']) for n,x in reports.items()},payload_bounds=payload),indent=2))
if __name__=='__main__':main()
