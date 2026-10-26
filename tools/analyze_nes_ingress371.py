# SPDX-License-Identifier: MIT
"""Whole boundary reconciliation for storage credit and hint/plan ownership."""
import argparse,inspect,json,re
from pathlib import Path
import analyze_nes_source368 as old
from analyze_nes_receipt335 import load_image
from nes_delta231 import ROOT,BASE,sha,once
from nes_ingress371 import COMMON,NAMES
from nes_bg295 import unbatch
from probe_nes_arm264 import ELFFile

# Same independent byte/read/receipt/credit/display checks. Only distinguish
# D5 flag1 storage release from flag3 semantic input ACK in the wire audit.
body=inspect.getsource(old.measure)
body=once(body,"elif tx[:1]==b'\\xd5':assert held is None and len(tx)==8;acks+=1",
 "elif tx[:1]==b'\\xd5':\n    assert held is None and len(tx)==8 and tx[5] in (1,3) and crc(tx[:6],8)==tx[6]\n    acks+=tx[5]==3")
ns=dict(old.__dict__);exec(compile(body,'measure371','exec'),ns);measure=ns['measure']

def symbols(p):
 with p.open('rb') as f:
  return {s.name:(s['st_value'],s['st_size']) for s in ELFFile(f).get_section_by_name('.symtab').iter_symbols() if s['st_info']['type'] in ('STT_FUNC','STT_OBJECT')}

def hierarchy(d):
 report=d/'output_files/board.map.rpt';old.PINS[str(report)]=sha(report);raw=report.read_bytes();out={}
 for b in raw.splitlines():
  if re.match(rb'^;\s*\|nes_(transport257|hint361|source_tile192|chr_cache192):[^|]+\|\s*;',b):
   cells=[x.strip() for x in b.decode('ascii').split(';')]
   out[cells[1]]=dict(comb_inclusive=int(cells[2].split()[0]),comb_self=int(re.search(r'\((\d+)\)',cells[2])[1]),FF_inclusive=int(cells[3].split()[0]))
 return out

def replacement_budget(d,required):
 names=('nes_core257:encoder','nes_transport257:transport','nes_spi270:spi_front270','nes_validator278:validator','nes_output260:flow','nes_plan_batch206:transport','nes_plan_spi200:endpoint')
 rows={}
 report=d/'output_files/board.map.rpt';old.PINS[str(report)]=sha(report)
 for b in report.read_bytes().splitlines():
  if not b.startswith(b';'):continue
  cells=b.decode('ascii',errors='replace').split(';')
  if len(cells)>3 and cells[1].strip().strip('|') in names:
   n=cells[1].strip().strip('|');rows[n]=int(re.search(r'\((\d+)\)',cells[2])[1])
 assert set(rows)==set(names)
 retained=rows[names[0]]+rows[names[3]];pool=sum(rows.values())-retained
 return dict(self_comb=rows,retained_codec_checker=retained,control_pool=pool,required_net=required,replacement_ceiling=pool-required,implemented_deletion_credit=0,scenario_only=True)

def timeline(d,rows,frame=914):
 row=next(x for x in rows if x['frame']==frame);start=row['start_ps'];ev=old.events(d)
 txs=old.js(d/f'arm{frame}.json')['transfers'];parts=[]
 for t in txs:
  tx=bytes.fromhex(t['tx']);phase=t.get('source_phase367',0)
  if phase or tx[:1]==b'\xd5' or (tx[:1]==b'\xea' and len(tx)==28):
   parts.append(dict(phase=phase,command=tx[0] if not phase and tx else None,flags=tx[5] if tx[:1]==b'\xd5' else None,bytes=len(tx),end_ms=(t['RTL_ns']*1000-start)/1e9,pending_instructions=t['instructions']))
 plan=d/f'actual-plans293-{frame}.bin';old.PINS[str(plan)]=sha(plan)
 bg=[int.from_bytes(p[5:7],'little') for p in unbatch(plan.read_bytes()) if p[0]==128]
 hint=row['hints'][0]['tags'];first_plan=next(t for t in txs if t['tx'].startswith('e9'))
 zero=next(x for x in ev if x[:3]==['romtile305',str(frame),'2'])
 from profile_nes_prepare353 import Profile
 snapshot=next(d.glob(f'causal368-{frame-904}-*.bin'));old.PINS[str(snapshot)]=sha(snapshot)
 arm=Profile(d/'output.elf');arm.uc.mem_write(0x20000000,snapshot.read_bytes());assert arm.call('source_hint367',[])==28
 instructions=arm.instructions;at=arm.call('source_buffer367',[])
 packet=next(t for t in txs if t['tx'].startswith('ea') and len(t['tx'])==56)
 assert bytes(arm.uc.mem_read(at,28)).hex()==packet['tx']
 return dict(frame=frame,source_parts=parts,first_plan_SPI_end_ms=(first_plan['RTL_ns']*1000-start)/1e9,
  first_zero_ms=(int(zero[-1])-start)/1e9,first_BG_ms=row['BG']['first_ms'],retrospective_BG_tags=bg,missing_from_initial_hint=[x for x in bg if x not in hint],
  hint_replay_instructions=instructions,hint_pending_instructions=packet['instructions'],
  future_information_used_for_hint=False,scope='Retrospective only;tag inclusion does not prove byte fill by ROM deadline;SPI remains synchronous.')

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--strict',type=Path);p.add_argument('--last',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 root=BASE/'probes/nes-source371';d=a.run.resolve();read=old.read;js=old.js
 log=read(d/'vsim.log');miss=int('Fatal: capture coverage367' in log)
 current=measure(d,a.last,miss);before=old.measure(BASE/'probes/nes-source370/joint02',914,1);pairs=[]
 strict_check=None
 if a.strict:
  strict=a.strict.resolve();s=read(strict/'vsim.log');m=re.search(r'Fatal: next capture deadline missed367 frame(\d+)',s);assert m
  frame=int(m[1]);left=old.events(strict);right=old.events(d)
  def prefix(ev):return ev[:next(i for i,x in enumerate(ev) if x[:2]==['capture_attempt367',str(frame)])+1]
  assert prefix(left)==prefix(right) and load_image(strict/'output.elf')==load_image(d/'output.elf')
  strict_check=dict(first_miss=frame,all_events_before_failure_exact=True)
 for x,y in zip(current['rows'][2:],before['rows'][2:]):
  assert x['frame']==y['frame'];same=(x['start_ps'],x['start_ROM_cycle'])==(y['start_ps'],y['start_ROM_cycle'])
  if x['frame']<=908:assert same
  pairs.append(dict(frame=x['frame'],before_ms=y['processing_ms'],after_ms=x['processing_ms'],delta_ms=x['processing_ms']-y['processing_ms'],same_start_ROM_phase=same,
   before_materialized_ms=y['materialized_ms'],after_materialized_ms=x['materialized_ms'],
   total_SPI_bytes_before=y['total_SPI_bytes'],total_SPI_bytes_after=x['total_SPI_bytes'],
   source_SPI_bytes_including_D5_before=y['source_SPI_bytes']+8,source_SPI_bytes_including_D5_after=x['source_SPI_bytes']+8*x['blocks']))
 wire=[]
 for row in current['rows']:
  tr=js(d/f"arm{row['frame']}.json")['transfers'];credit=final=0;seen=False;held=None;last_token=None
  for t in tr:
   tx=bytes.fromhex(t['tx']);rx=bytes.fromhex(t['rx']);phase=t.get('source_phase367',0)
   if phase==1:
    assert not seen and held is None and tx[5]==0
    last_token=int.from_bytes(tx[1:3],'big');assert last_token==int.from_bytes(rx[10:12],'big');held=rx[9]
   elif phase==2:
    assert held is not None;seen=bool(held);held=None
   elif tx[:1]==b'\xd5':
    assert seen and int.from_bytes(tx[1:3],'big')==last_token and int.from_bytes(tx[3:5],'little')==row['frame']-904
    credit+=tx[5]==1;final+=tx[5]==3;seen=False
  assert final==1 and credit==row['blocks']-1 and not seen and held is None
  wire.append(dict(frame=row['frame'],storage_releases=credit,semantic_ACK=final,storage_release_wire_bytes=credit*8))
  row['source_control_release_bytes']=8*(credit+final)
  row['source_SPI_bytes_including_D5']=row['source_SPI_bytes']+8*(credit+final)
 board=root/'map01';m=js(board/'result.json');previous=js(BASE/'probes/nes-source368/map01/result.json')
 for n in COMMON:
  read(d/n);read(board/n);assert sha(d/n)==sha(board/n)==m['shared_boundary'][n]
 canon=js(ROOT/'src/fpga/nes_ingress371/manifest.json')['source_files']
 for n,h in canon.items():assert sha(d/n)==sha(ROOT/'src/fpga/nes_ingress371'/n)==h
 report_after=old.whole(board);report_before=old.whole(BASE/'probes/nes-source368/map01');rx=old.whole(root/'map-rx01')
 delta={k:report_after[k]-report_before[k] for k in report_after}
 assert delta==dict(LE=37,comb=37,FF=1,RAM_bits=0)
 assert load_image(d/'output.elf')==load_image(root/'build09/output.elf')
 assert symbols(d/'output.elf')==symbols(root/'build09/output.elf')
 assert load_image(d/'pre371-output.elf')==load_image(BASE/'probes/nes-source370/joint02/output.elf')
 guards={n:js(root/n) for n in ('armwarm08.json','armguards05.json')};assert all(x['passed'] for x in guards.values())
 # Linker metadata differs between directories; executed PT_LOAD images must
 # match exactly, and both guards must pin that normalized reference ELF.
 reference_ELF=root/'build09/output.elf';old.PINS[str(reference_ELF)]=sha(reference_ELF)
 assert sha(reference_ELF) in guards['armwarm08.json']['pins'].values()
 assert sha(reference_ELF) in guards['armguards05.json']['pins'].values()
 for f in ('handoff03','credit01'):
  g=js(root/f/'result.json');assert g['passed'];guards[f]=g
  for path,h in g['pins'].items():
   n=Path(path).name
   if n in COMMON:read(d/n);assert sha(d/n)==h
 from guard_nes_handoff371 import TB as HANDOFF_TB
 from guard_nes_credit371 import TB as CREDIT_TB
 assert read(root/'handoff03/handoff371_tb.sv')==HANDOFF_TB
 assert read(root/'credit01/credit371_tb.sv')==CREDIT_TB
 assert read(root/'handoff03/hint371.sv')=='module nes_hint361'+read(d/'nes_plan_path267.sv').split('module nes_hint361',1)[1]
 compiled=set(re.findall(r'-name SYSTEMVERILOG_FILE\s+"?([^\s"]+)',read(board/'board.qsf')))
 assert set(COMMON)<=compiled
 modules={};all_shared={}
 for name in compiled:
  if (board/name).exists():
   for mod in re.findall(r'^\s*module\s+(\w+)',read(board/name),re.M):modules[mod]=board/name
 for name in js(d/'manifest367.json')['sources']:
  for mod in re.findall(r'^\s*module\s+(\w+)',read(d/name),re.M):
   if mod in modules:assert sha(d/name)==sha(modules[mod]);all_shared[mod]=sha(d/name)
 assert len(all_shared)==30
 for name in ('nes_receive371.c','nes_ingress371.py','probe_nes_ingress371.py'):
  executed=read(d/name);current_source=read(ROOT/'tools'/name)
  # arm() inserts C through read_text(),which normalizes Windows newlines.
  # Keep the raw archived bytes/pins and compare its actual inserted text.
  if name=='nes_receive371.c':assert executed==current_source
  else:assert sha(d/name)==sha(ROOT/'tools'/name)
 for p in ROOT.joinpath('tools').glob('*371.py'):read(p)
 read(ROOT/'tools/nes_receive371.c')
 costs=dict(before=old.size(d/'pre371-output.elf'),after=old.size(d/'output.elf'))
 costs['delta']={k:costs['after'][k]-costs['before'][k] for k in costs['before']}
 warm=current['rows'][2:];worst=max(warm,key=lambda x:x['processing_ms'])
 failures={}
 for name in ('joint03','joint04','joint05','joint06','joint08'):
  path=root/name/'vsim.log';s=read(path);match=re.search(r'Fatal: next capture deadline missed367 frame(\d+)',s)
  assert match;failures[name]=dict(first_missed_capture=int(match[1]),passed=False,vsim_log_sha256=sha(path))
 result=dict(stage=371,analysis_passed=True,continuous_capture_passed=current['continuous_capture_passed'],candidate=current,baseline370=before,paired=pairs,wire=wire,
  whole_MAP=dict(before=report_before,after=report_after,delta=delta,RX_only=rx,source_clock_domain_costs_before=hierarchy(BASE/'probes/nes-source368/map01'),source_clock_domain_costs_after=hierarchy(board),new_MAP=True),
  ARM_size=costs,guards=guards,shared_boundary={n:sha(d/n) for n in COMMON},all_shared_modules=all_shared,comb_deficit=report_after['comb']-15408,deletion_needed_with155reserve=report_after['comb']-15253,
  replacement_budget=replacement_budget(board,report_after['comb']-15253),
  failed_variants=failures,worst_warm_frame=worst['frame'],worst_warm_ms=worst['processing_ms'],warm_budget_margin_ms=1000/60-worst['processing_ms'],
  strict_diagnostic_check=strict_check,
  bounded_warm_60Hz_budget_passed=all(x['processing_ms']<=1000/60 for x in warm),
  timeline914=timeline(d,current['rows']),
  synchronous_SPI=True,DMA_overlap_claimed=False,FIT=False,STA=False,physical=False,sustained60fps=False,
  guarded_ELF_load_images_and_symbols_equal=True,
  candidate_selected_for_physical=False,candidate_selected_as_performance_baseline=False,recommended_timing_baseline=370,
  scope='Actual compiled M4 RX/record semantic/hint and physical SPI/IRQ adapters;independent FPGA read CRC/coverage/finalACK. CPI1/84MHz and peripherals allocated;ordinary65816 trace/map DMA+display busmodel,not fullCPU/VBlank/WCET/71/heavy7/multiple phases/physical.',pins=old.PINS)
 a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',newline='\n')
 print(json.dumps(dict(paired=pairs,captures=current['captures'],MAP=report_after,RX_MAP=rx,ARM=costs),indent=2))
if __name__=='__main__':main()
