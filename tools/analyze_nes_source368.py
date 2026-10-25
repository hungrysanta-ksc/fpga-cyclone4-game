# SPDX-License-Identifier: MIT
"""Separate hint/CRC, collector rearm and output backlog; reconcile whole cost."""
import ast,csv,hashlib,json,re,struct,subprocess
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from nes_capture368 import COMMON
from probe_nes_arm264 import crc
from analyze_nes_receipt335 import completed_unit,load_image
from analyze_nes_hint367 import hierarchy
PINS={}
def read(p):p=Path(p);PINS[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
def js(p):return json.loads(read(p))
def events(d):return list(csv.reader(read(d/'joint-events.csv').splitlines()))
def event(e,name,frame):return next(x for x in e if x[:2]==[name,str(frame)])
def whole(d):
 r=js(d/'result.json');assert r['passed'] and not r['undriven']
 return {k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',r['summary'])[1].replace(',','')) for k,v in dict(LE='Total logic elements',comb='Total combinational functions',FF='Dedicated logic registers',RAM_bits='Total memory bits').items()}
def size(p):
 tool=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin/arm-none-eabi-size.exe'
 PINS[str(p)]=sha(p);raw=subprocess.check_output([str(tool),str(p)]);(p.parent/(p.stem+'-size368.log')).write_bytes(raw)
 return dict(zip(('text','data','BSS'),map(int,raw.splitlines()[1].split()[:3])))

def measure(d,last,missed):
 log=read(d/'vsim.log');arm=js(d/'arm-result.json');m=js(d/'manifest368.json');ev=events(d)
 assert arm['passed'] and [x['frame'] for x in arm['frames']]==list(range(905,last+1))
 if missed:assert m['observe_last'] and 'Fatal: capture coverage367' in log and 'Errors: 1, Warnings: 0' in log
 else:assert js(d/'result.json')['passed'] and 'Errors: 0, Warnings: 0' in log
 rows=[]
 for a in arm['frames']:
  f=a['frame'];s=event(ev,'start319',f);start=int(s[2]);end=int(event(ev,'frame_done',f)[2]);txs=js(d/f'arm{f}.json')['transfers']
  hints=[];source_bytes=0;held=None;blocks=0;acks=0
  for t in txs:
   tx=bytes.fromhex(t['tx']);rx=bytes.fromhex(t['rx']);phase=t.get('source_phase367',0)
   if phase==1:
    assert held is None and len(tx)==13 and crc(tx[:6],8)==tx[6] and crc(rx[8:12],8)==rx[12];held=rx[9];source_bytes+=13
   elif phase==2:
    assert held is not None and len(tx)==(held+2 if held else 0)
    if held:assert crc(rx[:held])==int.from_bytes(rx[held:],'big');blocks+=1
    source_bytes+=len(tx);held=None
   elif tx[:1]==b'\xea' and len(tx)==28:
    assert held is None and crc(tx[:26])==int.from_bytes(tx[26:],'little') and int.from_bytes(tx[8:12],'little')==f-904
    hints.append(dict(tags=list(struct.unpack('<7H',tx[12:26])),end_ms=(t['RTL_ns']*1000-start)/1e9))
   elif tx[:1]==b'\xd5':assert held is None and len(tx)==8;acks+=1
  assert held is None and acks==1 and blocks==a['source_blocks367'] and len(hints)==a['source_hints367']
  expected=[];actual=[];offset=0;token=None;writes=[];published=0
  for x in ev:
   if x[1]!=str(f):continue
   if x[0]=='read336':
    tok,op,section,pos,off,value,t=map(int,x[2:]);assert off==offset
    if not offset:token=tok
    assert tok==token;offset+=1;unit=completed_unit(op,section,pos,2)
    if unit:expected.append((tok,int(unit[0]),unit[1]))
   elif x[0]=='unit336':actual.append(tuple(map(int,x[2:5])))
   elif x[0]=='private336':
    tok,addr,value,t=map(int,x[2:]);assert tok==token;writes.append(t)
   elif x[0]=='publish336':
    tok,n,t=map(int,x[2:]);assert tok==token and n==offset and n>0 and all(v<t for v in writes)
    offset=0;token=None;writes=[];published+=1
  assert expected==actual and not offset and int(event(ev,'display266',f)[2])==12*(f-904)
  credit=max(int(x[2]) for x in ev if x[:2]==['credits',str(f)]);assert credit<=2
  retire=event(ev,'retired368',f-904);assert int(retire[2])<=end
  row=dict(frame=f,start_ps=start,start_ROM_cycle=int(s[3]),processing_ms=(end-start)/1e9,
   materialized_ms=(int(event(ev,'materialized366',f)[3])-start)/1e9,input_ACK_ms=(int(event(ev,'input_done337',f)[3])-start)/1e9,
   actual_retired_ms=(int(retire[2])-start)/1e9,source_instructions=a['source_instructions367'],ARM_instructions=a['instructions'],
   source_SPI_bytes=source_bytes,total_SPI_bytes=a['SPI_bytes'],hints=hints,blocks=blocks,credit=credit,published=published,qualified_units=len(actual),independent_read_accounting=True)
  for kind in (0,1):
   tiles=[x for x in ev if x[:3]==['romtile305',str(f),str(kind)]]
   if tiles:row['BG' if kind==0 else 'OBJ']=dict(first_ms=(int(tiles[0][-1])-start)/1e9,last_ms=(int(tiles[-1][-1])-start)/1e9)
  rows.append(row)
 attempts=[]
 for x in ev:
  if x[0]=='capture_attempt367':
   f=int(x[1]);seal=event(ev,'materialized366',f-1)
   attempts.append(dict(frame=f,admitted=x[3]=='1',owned=int(x[2]),at_ps=int(x[5]),handoff_margin_ms=(int(x[5])-int(seal[3]))/1e9))
 assert len(attempts)==last-906 and sum(not x['admitted'] for x in attempts)==missed
 core=re.search(r'CAPTURE365 input_core=(\d+) replies=(\d+)',log);assert core
 audit=re.search(r'ROM368 requests=(\d+) replies=(\d+) pending=(\d+) input_requests=(\d+) input_replies=(\d+) input_pending=(\d+)',log)
 accounting=None
 if audit:
  req,rep,pending,ireq,irep,ipending=map(int,audit.groups())
  assert req-rep==pending and ireq-irep==ipending and pending in (0,1) and 0<=ipending<=pending
  accounting=dict(requests=req,replies=rep,pending=pending,input_requests=ireq,input_replies=irep,input_pending=ipending,origin_phase_matched=True)
 else:assert core[1]==core[2]
 if m['no_bitmap']:assert 'QUERY368 kinds=b7' in log
 return dict(rows=rows,captures=attempts,continuous_capture_passed=not missed,missed=missed,legacy_phase_window_ROM_requests=int(core[1]),legacy_phase_window_ROM_replies=int(core[2]),ROM_origin_accounting=accounting,stack_observed=arm['stack_observed'],IRQ_bodies=len(arm['IRQ_cases']),EXTI_events=len(arm['EXTI284']))

def main():
 root=BASE/'probes/nes-source368';selected=root/'joint07';control=root/'control01';board=root/'map01'
 runs=dict(candidate=measure(selected,910,1),control=measure(control,909,1),before_used_filter=measure(root/'joint04',910,1));pairs=[]
 for x,y in zip(runs['candidate']['rows'][2:],runs['control']['rows'][2:]):
  assert (x['frame'],x['start_ps'],x['start_ROM_cycle'])==(y['frame'],y['start_ps'],y['start_ROM_cycle'])
  pairs.append(dict(frame=x['frame'],candidate_ms=x['processing_ms'],control_ms=y['processing_ms'],delta_ms=x['processing_ms']-y['processing_ms'],same_start_ROM_phase=True))
 # ARM-only and old-core joint strict failures are evidence, never passes.
 arm_only=events(root/'fixed01');assert 'Fatal: next capture deadline missed367 frame910' in read(root/'fixed01/vsim.log')
 seal=event(arm_only,'materialized366',909);attempt=event(arm_only,'capture_attempt367',910)
 assert attempt[2:4]==['0','0'];arm_margin=(int(attempt[5])-int(seal[3]))/1e9
 strict=read(root/'joint03/vsim.log');assert 'Fatal: next capture deadline missed367 frame911 owned1 initialized1 release0 fault0' in strict
 m=js(selected/'manifest368.json');bm=js(board/'result.json');shared={}
 compiled=set(re.findall(r'-name SYSTEMVERILOG_FILE\s+"?([^\s"]+)',read(board/'board.qsf')));assert set(COMMON)<=compiled
 for n in COMMON:
  read(selected/n);read(board/n);assert sha(selected/n)==sha(board/n)==m['shared_boundary'][n]==bm['shared_boundary'][n];shared[n]=sha(selected/n)
 canonical=js(ROOT/'src/fpga/nes_source368/manifest.json')['source_files']
 for n,h in canonical.items():read(ROOT/'src/fpga/nes_source368'/n);assert sha(ROOT/'src/fpga/nes_source368'/n)==h==shared[n]
 all_shared={};modules={}
 for name in compiled:
  if (board/name).exists():
   for mod in re.findall(r'^\s*module\s+(\w+)',read(board/name),re.M):modules[mod]=board/name
 for name in js(selected/'manifest367.json')['sources']:
  for mod in re.findall(r'^\s*module\s+(\w+)',read(selected/name),re.M):
   if mod in modules:assert sha(selected/name)==sha(modules[mod]);all_shared[mod]=sha(selected/name)
 after=whole(board);before=whole(BASE/'probes/nes-hint367/map02');delta={k:after[k]-before[k] for k in after}
 old_report=read(BASE/'probes/nes-hint367/map02/output_files/board.map.rpt');new_report=read(board/'output_files/board.map.rpt')
 assert '|altsyncram:required_tiles_rtl_0|' in old_report and '|altsyncram:required_tiles_rtl_0|' not in new_report and delta['RAM_bits']==-16384
 guards={n:js(root/n/'result.json') for n in ('guards06','bitmap01','query01','session01')};assert all(x['passed'] for x in guards.values())
 assert guards['guards06']['ELF']==sha(selected/'output.elf') and guards['bitmap01']['pins']['nes_native_planes165.sv']==shared['nes_native_planes165.sv']
 assert guards['session01']['pins']['nes_native_capture365.sv']==shared['nes_native_capture365.sv']
 profile=js(root/'profile368.json');assert profile['passed'] and profile['CRC_vectors']==1280
 assert load_image(root/'joint05/output.elf')==load_image(selected/'output.elf')
 for name in ('nes_capture368.py','probe_nes_source368.py','nes_source368.py'):
  assert ast.dump(ast.parse(read(ROOT/'tools'/name)))==ast.dump(ast.parse(read(selected/name)))
 read(ROOT/'tools/nes_source368.c');read(selected/'nes_source368.c');assert sha(ROOT/'tools/nes_source368.c')==sha(selected/'nes_source368.c')
 old_hint=js(BASE/'probes/nes-hint367/hintguards02/result.json');assert old_hint['passed']
 for path,h in old_hint['pins'].items():
  name=Path(path).name
  if name in ('nes_spi270.sv','nes_plan_spi200.sv','nes_source_tile192.sv','nes_chr_cache192.sv','nes_tile205.sv','nes_native_arbiter165.sv','nes_rom_physical.sv'):
   read(selected/name);assert sha(selected/name)==h
 old_hint_module=read(BASE/'probes/nes-hint367/hintguards02/nes_hint361.sv');current_hint_module=read(selected/'nes_plan_path267.sv')
 assert current_hint_module[current_hint_module.index('module nes_hint361'):]==old_hint_module
 cost=dict(before=size(selected/'pre368-output.elf'),after=size(selected/'output.elf'));cost['delta']={k:cost['after'][k]-cost['before'][k] for k in cost['before']}
 for p in ROOT.joinpath('tools').glob('*368.py'):read(p)
 read(ROOT/'tools/nes_source368.c')
 result=dict(stage=368,analysis_passed=True,passed=True,candidate_selected_for_physical=False,continuous_capture_passed=False,runs=runs,paired=pairs,
  ARM_only_910_owned=0,ARM_only_910_admitted=False,ARM_only_handoff_margin_ms=arm_margin,legacy_scrub_clocks=8192,
  strict_joint_first_miss=911,shared_boundary=shared,all_shared_modules=all_shared,guards=guards,profile=profile,
  whole_MAP=dict(before=before,after=after,delta=delta),ARM_size=cost,comb_deficit=after['comb']-15408,deletion_needed_with155reserve=after['comb']-15253,
  source_query6='Source cursor selector never emits6; selected collector rejects it; default path and plane/event/error checks retained.',
  completion='Generation-checked actual flow_retired edge retained across next source start; no synthetic ACK.',
  limits=['Compiled ARM C at allocated CPI1/84MHz; IRQ bodies plus24entry/exitcycles,not hardware WCET.','Ready-gated ROM stress during input/output,not live NES CPU.','Ordinary65816 trace replay;map DMA/final display busmodels;unchanged VBlank firmware,not fullCPU proof.','905/906 serialized startup;frame907 capture fixed at predeclared5371247clock,then357368clock cadence.','Full71/heavy7/FIT/STA/physical60fps remain open.'],FIT=False,STA=False,physical=False,sustained60fps=False,pins=PINS)
 (ROOT/'analysis/source368-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',newline='\n')
 print(json.dumps({k:result[k] for k in ('paired','whole_MAP','ARM_size','ARM_only_handoff_margin_ms','comb_deficit')},indent=2))
if __name__=='__main__':main()
