# SPDX-License-Identifier: MIT
"""Same-start causal hint experiment, actual foreground, continuous capture, whole Lite."""
import ast,csv,json,re,subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_hint367 import COMMON
from probe_nes_arm264 import crc
from analyze_nes_receipt335 import completed_unit,load_image
from nes_bg295 import unbatch
PINS={}
def read(p):
 p=Path(p);PINS[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
def js(p):return json.loads(read(p))
def events(d):return list(csv.reader(read(d/'joint-events.csv').splitlines()))
def event(e,name,f):return next(x for x in e if x[:2]==[name,str(f)])
def whole(d):
 r=js(d/'result.json');assert r['passed'] and not r['undriven']
 return {k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',r['summary'])[1].replace(',','')) for k,v in dict(LE='Total logic elements',comb='Total combinational functions',FF='Dedicated logic registers',RAM_bits='Total memory bits').items()}
def size(p):
 tool=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin/arm-none-eabi-size.exe'
 PINS[str(p)]=sha(p);raw=subprocess.check_output([str(tool),str(p)])
 (p.parent/(p.stem+'-size367.log')).write_bytes(raw)
 return dict(zip(('text','data','BSS'),map(int,raw.splitlines()[1].split()[:3])))
def hierarchy(d):
 report=read(d/'output_files/board.map.rpt');out={}
 for name in ('nes_core257:encoder','nes_transport257:transport','nes_spi270:spi_front270','nes_validator278:validator','nes_output260:flow','nes_plan_batch206:transport','nes_plan_spi200:endpoint'):
  line=next(x for x in report.splitlines() if re.search(r'^;\s*\|'+re.escape(name)+r'\|\s*;',x))
  cells=[x.strip() for x in line.split(';')]
  out[name]=dict(comb_inclusive=int(cells[2].split()[0]),comb_self=int(re.search(r'\((\d+)\)',cells[2])[1]),FF_inclusive=int(cells[3].split()[0]),RAM_inclusive=int(cells[4]))
 return out

def run(d,strict_partial=False):
 manifest=js(d/'manifest367.json');e=events(d);rows=[];log=read(d/'vsim.log')
 if (d/'result.json').exists():
  r=js(d/'result.json');assert r['passed'] and 'Errors: 0, Warnings: 0' in log
 else:
  # A drained diagnostic is NOT a continuous-capture pass. Keep the earlier
  # strict immediate failure separately, and measure the rejected deadline.
  assert re.search(r'Errors: 1, Warnings: \d+',log)
  if strict_partial:
   assert 'Fatal: next capture deadline missed367 frame910' in log and 'Warnings: 0' in log
   completed=[json.loads(x) for x in read(d/'arm-worker.log').splitlines() if x.startswith('{')]
   assert [x['frame'] for x in completed]==list(range(905,909))
   arm=dict(frames=completed,stack_observed=None,IRQ_cases=[],EXTI284=[])
  else:
   assert manifest['observe_miss'] and 'Fatal: capture coverage367' in log
   warnings=[x for x in log.splitlines() if '** Warning:' in x]
   assert len(warnings)==32 and all('(vsim-3534) [FOFIR] - Failed to open file "arm-result.json" for reading.' in x for x in warnings)
   arm=js(d/'arm-result.json');assert arm['passed'] and [x['frame'] for x in arm['frames']]==list(range(905,910))
  r=dict(passed=False,frames=len(arm['frames']),ARM=arm,ELF_sha256=sha(d/'output.elf'),rtl_hashes={n:sha(d/n) for n in manifest['sources']})
 counts=re.search(r'CAPTURE365 input_core=(\d+) replies=(\d+)',log);assert counts and counts[1]==counts[2]
 for a in r['ARM']['frames']:
  f=a['frame'];s=event(e,'start319',f);end=event(e,'frame_done',f);start=int(s[2])
  tr=js(d/f'arm{f}.json')['transfers'];hints=[];prefixes=0;payloads=0;source_bytes=0;held=None;input_ack=0;waits=0
  for t in tr:
   tx=bytes.fromhex(t['tx']);rx=bytes.fromhex(t['rx']);phase=t.get('source_phase367',0)
   if phase==1:
    assert held is None and len(tx)==13 and tx[0]==0xd4 and crc(tx[:6],8)==tx[6]
    assert crc(rx[8:12],8)==rx[12];held=rx[9];prefixes+=1;source_bytes+=13
   elif phase==2:
    assert held is not None and len(tx)==(held+2 if held else 0)
    if held:assert crc(rx[:held])==int.from_bytes(rx[held:],'big');payloads+=1
    source_bytes+=len(tx);held=None
   elif tx[:1]==b'\xea' and len(tx)==28:
    assert held is None and tx[1]==7 and crc(tx[:26])==int.from_bytes(tx[26:],'little')
    assert int.from_bytes(tx[8:12],'little')==f-904
    hints.append(dict(tags=[int.from_bytes(tx[i:i+2],'little') for i in range(12,26,2)],end_ms=(t['RTL_ns']*1000-start)/1e9))
   elif tx[:1]==b'\xd5':assert held is None and len(tx)==8;input_ack+=1
   waits+=bool(t.get('wait284'))
  assert held is None and input_ack==1 and payloads==a['source_blocks367'] and len(hints)==a['source_hints367']
  # Independent consumer accounting: actual reads -> units -> private writes -> publish.
  expected=[];actual=[];offset=0;token=None;writes=[];published=0
  for x in e:
   if x[1]!=str(f):continue
   if x[0]=='read336':
    tok,op,section,pos,off,data,t=map(int,x[2:]);assert off==offset
    if not offset:token=tok
    assert tok==token;offset+=1;u=completed_unit(op,section,pos,2)
    if u:expected.append((tok,int(u[0]),u[1]))
   elif x[0]=='unit336':actual.append(tuple(map(int,x[2:5])))
   elif x[0]=='private336':
    tok,addr,value,t=map(int,x[2:]);assert tok==token;writes.append(t)
   elif x[0]=='publish336':
    tok,n,t=map(int,x[2:]);assert tok==token and n==offset and n>0 and all(v<t for v in writes)
    offset=0;token=None;writes=[];published+=1
  assert expected==actual and offset==0 and int(event(e,'display266',f)[2])==12*(f-904)
  credit=max(int(x[2]) for x in e if x[:2]==['credits',str(f)]);assert credit<=2
  done=(int(end[2])-start)/1e9
  row=dict(frame=f,start_ps=start,start_ROM_cycle=int(s[3]),processing_ms=done,excess_60Hz_ms=max(0,done-1000/60),
   materialized_ms=(int(event(e,'materialized366',f)[3])-start)/1e9,
   input_ACK_ms=(int(event(e,'input_done337',f)[3])-start)/1e9,
   source_instructions=a['source_instructions367'],ARM_instructions=a['instructions'],source_blocks=payloads,
   source_SPI_bytes=source_bytes,source_CS_transactions=prefixes+1,source_empty_polls=a['source_empty367'],
   hint_SPI_bytes=28*len(hints),hints=hints,total_shared_SPI_bytes=a['SPI_bytes'],WFI_calls=waits,
   output_progress_polls=sum(t['tx'].startswith('e2') and not t.get('source_phase367') for t in tr),credit=credit,
   qualified_units=len(actual),published=published,independent_read_accounting=True)
  for kind in (0,1):
   values=[x for x in e if x[:3]==['romtile305',str(f),str(kind)]]
   if values:row['BG' if not kind else 'OBJ']=dict(first_tile_ms=(int(values[0][-1])-start)/1e9,last_tile_ms=(int(values[-1][-1])-start)/1e9,tiles=len(values))
  fills=[x for x in e if x[:2]==['hint_fill367',str(f)]]
  row['hint_fill_ms']=[(int(x[2])-start)/1e9 for x in fills];rows.append(row)
  plan_path=d/f'actual-plans293-{f}.bin';PINS[str(plan_path)]=sha(plan_path)
  identity_BG=[int.from_bytes(p[5:7],'little') for p in unbatch(plan_path.read_bytes()) if p[0]==128]
  row['identity_BG_plan_tags']=identity_BG
  row['identity_BG_missing_from_hint']=sorted(set(identity_BG)-{tag for hint in hints for tag in hint['tags']})
 attempts=[]
 for x in e:
  if x[0]=='capture_attempt367':
   f=int(x[1]);prev=event(e,'start319',f-1);handoff=next((v for v in e if v[:2]==['materialized366',str(f-1)]),None);admitted=x[3]=='1'
   assert (x[2]=='0')==admitted
   attempts.append(dict(frame=f,admitted=admitted,collector_owned=int(x[2]),at_ps=int(x[5]),margin_after_handoff_ms=(int(x[5])-int(handoff[3]))/1e9 if handoff else None))
 assert len(attempts)==r['frames']-2+int(strict_partial)
 misses=sum(not x['admitted'] for x in attempts);assert misses==(0 if r['passed'] else 1)
 return dict(rows=rows,capture_attempts=attempts,continuous_capture_passed=not misses,missed_captures=misses,input_ROM_core_requests=int(counts[1]),stack_observed=r['ARM']['stack_observed'],IRQ_bodies=len(r['ARM']['IRQ_cases']),EXTI_events=len(r['ARM']['EXTI284'])),r,e

def main():
 root=BASE/'probes/nes-hint367';selected=root/'long02';control=root/'control01';board=root/'map02'
 runs={};runs['candidate'],r,e=run(selected);runs['control'],c,ce=run(control)
 runs['hint_only'],hr,he=run(root/'long01',strict_partial=True)
 assert load_image(selected/'output.elf')==load_image(control/'output.elf')==load_image(root/'long01/output.elf')
 paired=[]
 for x,y in zip(runs['candidate']['rows'],runs['control']['rows']):
  assert (x['frame'],x['start_ps'],x['start_ROM_cycle'])==(y['frame'],y['start_ps'],y['start_ROM_cycle'])
  paired.append(dict(frame=x['frame'],candidate_ms=x['processing_ms'],control_ms=y['processing_ms'],delta_ms=x['processing_ms']-y['processing_ms'],same_start_and_ROM_phase=True))
 m=js(board/'result.json');hashes={}
 canonical=js(ROOT/'src/fpga/nes_hint367/manifest.json')['source_files']
 for n in COMMON:
  read(selected/n);read(control/n);read(board/n)
  assert sha(selected/n)==sha(board/n)==r['rtl_hashes'][n]==m['shared_boundary'][n];hashes[n]=sha(selected/n)
  if n=='nes_core257.sv':assert sha(control/n)==sha(ROOT/'src/fpga/nes_capture365'/n)
  else:assert sha(control/n)==sha(selected/n)
  source=(ROOT/'src/fpga/nes_hint367'/n) if n in canonical else (ROOT/'src/fpga'/n) if n in ('nes_native_capture365.sv','nes_capture_lease366.sv') else (ROOT/'src/fpga/nes_capture365'/n)
  read(source);assert sha(source)==hashes[n]
  if n in canonical:assert canonical[n]==hashes[n]
 qsf=read(board/'board.qsf');compiled=set(re.findall(r'-name SYSTEMVERILOG_FILE\s+"?([^\s"]+)',qsf));assert set(COMMON)<=compiled
 modules={}
 for n in compiled:
  p=board/n
  if p.exists():
   for name in re.findall(r'^\s*module\s+(\w+)',read(p),re.M):modules[name]=p
 all_shared={}
 for n,h in r['rtl_hashes'].items():
  for name in re.findall(r'^\s*module\s+(\w+)',read(selected/n),re.M):
   if name in modules:
    assert sha(modules[name])==h
    all_shared[name]=h
 guards={n:js(root/n/'result.json') for n in ('armguards05','irqguards01','hintguards02','rawguards02')}
 assert all(g['passed'] for g in guards.values()) and guards['armguards05']['ELF']==r['ELF_sha256']
 assert guards['rawguards02']['pins']['nes_core257.sv']==hashes['nes_core257.sv']
 retained=js(BASE/'probes/nes-capture365/guards04/result.json')
 assert retained['passed'] and retained['guards']==22 and retained['pins']['nes_native_capture365.sv']==hashes['nes_native_capture365.sv']
 read(BASE/'probes/nes-capture365/guards04/vsim.log')
 baseline=whole(BASE/'probes/nes-capture365/map03');new=whole(board);delta={k:new[k]-baseline[k] for k in new}
 ledger={name:hierarchy(folder) for name,folder in [('before',BASE/'probes/nes-capture365/map03'),('after',board)]}
 before=size(selected/'pre367-output.elf');after=size(selected/'output.elf')
 for name in ('nes_hint367.py','probe_nes_hint367.py'):
  assert ast.dump(ast.parse(read(ROOT/'tools'/name)))==ast.dump(ast.parse(read(selected/name)))
 for n in ('nes_hint367.py','probe_nes_hint367.py','nes_source367.c','map_nes_hint367.py','guard_nes_source367.py','guard_nes_irq367.py','guard_nes_hint367.py','guard_nes_handoff367.py','analyze_nes_hint367.py'):read(ROOT/'tools'/n)
 strict=read(root/'long01/vsim.log');assert 'Fatal: next capture deadline missed367 frame910' in strict and 'CADENCE367 attempts=3 admitted=2 missed=1' in strict
 hint_pairs=[]
 for x,y in zip(runs['hint_only']['rows'],runs['control']['rows']):
  assert (x['start_ps'],x['start_ROM_cycle'])==(y['start_ps'],y['start_ROM_cycle'])
  hint_pairs.append(dict(frame=x['frame'],candidate_ms=x['processing_ms'],control_ms=y['processing_ms'],delta_ms=x['processing_ms']-y['processing_ms'],same_RTL_start_and_ROM_phase=True))
 result=dict(stage=367,passed=True,analysis_passed=True,candidate_selected_for_physical=False,continuous_capture_passed=runs['candidate']['continuous_capture_passed'],
  hint_only_pairs=hint_pairs,
  loaded_ARM_images_identical=True,retained_session_guards=22,diagnostic_file_poll_warnings=32,
  strict_first_miss_frame=910,runs=runs,paired=paired,shared_boundary=hashes,all_shared_modules=all_shared,
  guards=guards,whole_MAP=dict(before=baseline,after=new,delta=delta),hierarchy_nonadditive=ledger,
  resource_interpretation='Whole MAP delta is measured; inclusive parents and children are not added. Source/SPI self costs need not decline when whole logic changes; no inferred deletion credit or FIT claim.',
  comb_deficit=new['comb']-15408,deletion_needed_with155reserve=new['comb']-15253,
  ARM_size=dict(before=before,after=after,delta={k:after[k]-before[k] for k in before}),
  actual_ARM_source=True,source_cost_replay=False,hint_future_plan_oracle=False,actual_shared_SPI=True,
  IRQ='Compiled SysTick/EXTI bodies plus allocated 24 entry/exit cycles; bounded peripheral adapter, not hardware WCET.',
  ROM='Declared ready-gated period120 NES-clock stress at001234 during both input/output; real physical-reader arbitration, not live NES CPU.',
  SNES='Existing ordinary65816 bus traces; DMA/final display remain bus models. Unchanged VBlank firmware is not a new full65816 proof.',
  FIT=False,STA=False,physical=False,sustained60fps=False,pins=PINS)
 (ROOT/'analysis/hint367-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',newline='\n')
 print(json.dumps(dict(paired=paired,candidate=runs['candidate']['rows'],whole_MAP=result['whole_MAP'],ARM_size=result['ARM_size']),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
