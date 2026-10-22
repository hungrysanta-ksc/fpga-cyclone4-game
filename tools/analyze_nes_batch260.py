# SPDX-License-Identifier: MIT
"""Recheck ARM/RTL/MAP evidence and build a payload-free conditional ledger."""
import argparse,collections,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_batch260 import sources
from probe_nes_arm260 import ELFFile,plans,verify,expand

def loaded_image(path):
 with path.open('rb') as f:
  elf=ELFFile(f)
  image=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
  symbols=[(s.name,s['st_value'],s['st_size']) for s in elf.get_section_by_name('.symtab').iter_symbols() if s['st_info']['type']!='STT_FILE']
  return image,symbols

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();out=a.out.resolve();assert not out.exists();out.mkdir(parents=True)
 plan=json.loads((ROOT/'docs/nes-batch260-plan.json').read_text(encoding='utf-8'));base=BASE/'probes/nes-batch260';pins={}
 def pin(f):pins[f.relative_to(BASE).as_posix()]=sha(f);return f
 def read(name):return json.loads(pin(base/name/'result.json').read_text())
 def raw(name,file):return pin(base/name/file).read_text(errors='replace')
 arm=read(plan['selected']['arm']);guards=read(plan['selected']['arm_guards'])
 assert arm['passed'] and len(arm['frames'])==71 and arm['max_queue_used']==4
 assert guards['passed'] and len(guards['cases'])==12 and guards['ELF_sha256']==arm['ELF_sha256']
 assert guards['counter_wrap']==dict(start=65530,final=41,packets=47,max_credit=4)
 ad=base/plan['selected']['arm'];assert sha(pin(ad/'output.elf'))==arm['ELF_sha256']
 assert sha(pin(ad/'nes_output260.c'))==arm['source_sha256']==sha(pin(ROOT/'tools/nes_output260.c'))
 for f in ad.glob('*.packets'):pin(f)
 for f in ad.glob('*.transfers.json'):pin(f)
 for n in ['size.log','disassembly.log','build.log']:pin(ad/n)
 unit=read(plan['selected']['guards']);assert unit['passed'] and len(unit['cases'])==70
 for s,g in unit['cases']:
  log=raw(plan['selected']['guards'],f'shared{s}-guard{g:02}/vsim.log')
  assert 'PASS BATCH260' in log and not re.search(r'\*\* (Error|Fatal):',log)
 legacy=read(plan['selected']['legacy']);assert legacy['passed'] and len(legacy['cases'])==34 and legacy['rtl_hashes']==unit['rtl_hashes']
 for ss,gg in legacy['cases']:assert 'PASS MUX258' in raw(plan['selected']['legacy'],f'shared{ss}-guard{gg:02}/vsim.log')
 assert (base/plan['selected']['guards']/'mux259_tb.sv').read_text()==(ROOT/'tests/nes-functional/batch260_tb.sv').read_text().replace('batch260_tb','mux259_tb')
 pin(ROOT/'tests/nes-functional/batch260_tb.sv')
 assert raw(plan['selected']['guards'],'shared0-guard00/events.csv')==raw(plan['selected']['guards'],'shared1-guard00/events.csv')
 def rtl(name,r):
  assert r['rtl_hashes']==unit['rtl_hashes'],name
  for n,h in r['rtl_hashes'].items():assert sha(pin(base/name/n))==h,(name,n)
 rtl(plan['selected']['guards'],unit)
 generated=sources()
 for n,s in generated.items():
  import hashlib
  assert hashlib.sha256(s.encode()).hexdigest()==unit['rtl_hashes'][n],n
 areas=[]
 for name in plan['selected']['maps']:
  r=read(name);rtl(name,r);assert r['passed'] and not r['FIT'] and not r['STA']
  assert r['test_sha256']==sha(pin(base/'rtl01/result.json'))
  summary=raw(name,'output_files/output.map.summary');assert summary==r['summary'] and 'Lite Edition' in summary
  pin(base/name/'map.log');report=pin(base/name/'output_files/output.map.rpt').read_text()
  assert 'State Machine - |nes_output260|state' in report and 'State Machine - |nes_output260|owner' in report and 'Encoding Type:  One-Hot' in report
  area=dict(shared=r['shared'])
  for key,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]:
   area[key]=int(re.search(label+r'\s*:\s*([\d,]+)',summary)[1].replace(',',''))
  areas.append(area)
 assert areas==[dict(shared=1,LE=3509,comb=2339,FF=1703,RAM_bits=41216)]
 old={}
 for r in csv.DictReader(pin(ROOT/'analysis/boundary256-costs.csv').open()):
  if r['setup']=='500' and r['retained_policy']=='command_tail' and r['accounting_policy']=='transfer_covered_conditional':old[int(r['frame'])]=float(r['source_rtl_ms'])
 rows=[];detail={};bus_image=None
 for name in plan['selected']['rtl']+plan['selected']['bus']:
  r=read(name);rtl(name,r);assert r['passed'] and r['source_sha256']==arm['source_sha256']
  assert sha(pin(base/name/'nes_output260.c'))==arm['source_sha256']
  log=raw(name,'vsim.log');assert 'PASS OUTPUT259' in log and not re.search(r'\*\* (Error|Fatal):',log)
  for n in ['vlog.log','output260_tb.sv','output.elf','size.log','events.csv','rpc.do']:pin(base/name/n)
  for n,h in r['input_hashes'].items():assert sha(pin(BASE/n))==h
  tr=json.loads(raw(name,'transfers.json'));groups=collections.defaultdict(lambda:dict(transactions=0,wire_bytes=0,instructions=0,map_values=0))
  for index,(tx,rx,ins) in enumerate(tr,1):
   delay,request=(base/name/f'req{index}').read_text().split()
   assert request==tx and float(delay)==round(ins*r['CPI_assumed']*1000/84,3)
   b=bytes.fromhex(tx);assert len(b)==len(bytes.fromhex(rx));key=f'op{b[1]}' if b[0]==0xe1 else f'cmd{b[0]:02x}'
   v=groups[key];v['transactions']+=1;v['wire_bytes']+=len(b);v['instructions']+=ins
   if key=='op14':
    ranges=expand(b[1:-2]);v['map_values']+=sum(len(q)-20 for q in ranges);v['map_ranges']=v.get('map_ranges',0)+len(ranges)
  assert sum(v['wire_bytes'] for v in groups.values())==r['SPI_bytes']
  shared=bool(r.get('shared_SPI_pins'));elapsed=r['observed']['host_ticks']/100000
  # GCC's temporary assembler object STT_FILE name varies in .strtab.
  # Compare every loaded byte/address/size and all non-file symbols instead.
  if not shared:
   assert loaded_image(base/name/'output.elf')==loaded_image(ad/'output.elf')
   assert (base/name/'output260_tb.sv').read_bytes()==pin(ROOT/'tests/nes-functional/output260_tb.sv').read_bytes()
  assert r['queue_final_sent']==((r['queue_seed']+r['packets'])&65535)
  # RTL reports final ACK before the ARM completes its last status/CRC.
  # Reconstruct the serialized driver schedule including that trailing work,
  # 10us initial ready, and10ns+1000ns per RPC transfer (rpc.do). Do not add
  # the diagnostic DONE100us settling wait to useful execution.
  trailing=r['ARM_instructions']-sum(i for tx,rx,i in tr);assert trailing>=0
  arm_end=.01+sum(round(i*r['CPI_assumed']*1000/84,3)/1e6+len(bytes.fromhex(tx))*3047.616/1e6+.00101 for tx,rx,i in tr)+trailing*r['CPI_assumed']/84000
  assert arm_end>=elapsed
  row=dict(run=name,frame=r['frame'],shared_input_output_SPI=shared,CPI_assumed=r['CPI_assumed'],tile_fetch_wait=r['tile_fetch_wait_NES_cycles'],ARM_instructions=r['ARM_instructions'],SPI_bytes=r['SPI_bytes'],RTL_final_ACK_ms=elapsed,ARM_completion_model_ms=arm_end,prior_source_ms='' if shared else old.get(r['frame'],''),conditional_source_plus_output_ms='' if shared or r['frame'] not in old else arm_end+old[r['frame']],remaining_display_and_full_RUN='unknown',physical_ms='')
  rows.append(row);detail[name]=dict(commands=dict(groups),observed=r['observed'],source_bytes=r.get('source_bytes'),input_ARM_instructions=r.get('input_ARM_instructions'))
  if shared:
   image=loaded_image(base/name/'output.elf')
   if bus_image is None:bus_image=image
   else:assert image==bus_image
   assert sha(pin(base/name/'nes_input259.c'))==sha(pin(ROOT/'tools/nes_input259.c'))
   pin(base/name/'source.hex');pin(base/name/'source-size.txt')
   assert r['source_query_timing_bound'] is False
   blocks=pin(BASE/'probes/nes-joint255/test03/blocks.txt').read_text().splitlines()
   source=b''.join(bytes.fromhex(line.split()[3]) for line in blocks if int(line.split()[0])==r['frame'])
   assert bytes.fromhex((base/name/'source.hex').read_text())==source and len(source)==r['source_bytes']
  # The initialized/expected metadata are historical C outputs, not a newly
  # executed N5 planner. Pin and compare both, including same-bank inheritance.
  gen=r['frame']-904;prior=BASE/'probes/nes-wholepath247/jointdecode-test02/run'
  expected=pin(prior/f'expected-{gen}.bin').read_bytes()
  assert bytes.fromhex(raw(name,'expected.hex'))==expected
  inherited=pin(prior/f'expected-{gen-2}.bin').read_bytes() if gen>2 else bytes(8570)
  assert bytes.fromhex(raw(name,'prior.hex'))==inherited
 # Expand actual batches and independently check the original plans/H2.
 packing=[];prior,planned=plans()
 certs=bytes.fromhex(pin(BASE/'probes/nes-joint255/test03/certs.hex').read_text())
 for row in arm['frames']:
  data=pin(ad/f"frame{row['frame']}.packets").read_bytes();at=0;packets=[]
  while at<len(data):
   n=int.from_bytes(data[at:at+2],'little');at+=2;packets.append(data[at:at+n]);at+=n
  assert at==len(data);verify(planned[row['serial']],packets)
  batches=[p for p in packets if p[0]==14];records=[q for p in batches for q in expand(p)]
  assert [p[16:] for p in packets if p[0]==13]==[certs[(row['serial']-1)*32:row['serial']*32]]
  values=sum(len(p)-20 for p in records);oldwire=sum(len(p)+3 for p in records);wire=sum(len(p)+3 for p in batches)
  packing.append(dict(frame=row['frame'],ranges=len(records),values=values,batch_packets=len(batches),old_map_wire=oldwire,batch_map_wire=wire,wire_only_saved_ms=(oldwire-wire)*8/2625))
 assert sum(r['ranges'] for r in packing)==arm['range_steps']==2069
 assert sum(r['batch_packets'] for r in packing)==124 and arm['held_polls']==1945
 previous=json.loads(pin(ROOT/'analysis/output259-verification.json').read_text())
 comparison=[]
 for r in rows:
  matches=[q for q in previous['rows'] if q['frame']==r['frame'] and q['CPI_assumed']==r['CPI_assumed'] and q['tile_fetch_wait']==r['tile_fetch_wait'] and q['shared_input_output_SPI']==r['shared_input_output_SPI'] and q['run']!='wrap01']
  if r['run']=='wrap01':continue
  if matches:
   q=matches[0];comparison.append(dict(run=r['run'],frame=r['frame'],old_run=q['run'],old_SPI_bytes=q['SPI_bytes'],new_SPI_bytes=r['SPI_bytes'],old_ARM_completion_ms=q['ARM_completion_model_ms'],new_ARM_completion_ms=r['ARM_completion_model_ms'],saved_ms=q['ARM_completion_model_ms']-r['ARM_completion_model_ms']))
 result=dict(passed=True,stage=260,selected=plan['selected'],scope='Actual Cortex-M4 instructions and output RTL; modeled SNES service/CPI/tile fetch. Diagnostic shared SPI source transport; no full N5 planner/RUN or board time.',arm={k:v for k,v in arm.items() if k!='frames'},ARM_guard_cases=len(guards['cases']),ARM_counter_wrap=guards['counter_wrap'],RTL_guard_runs=len(unit['cases']),areas=areas,rows=rows,detail=detail,actual_packing=packing,comparison=comparison,legacy_guard_runs=len(legacy["cases"]),area_change_vs259=dict(LE=227,comb=267,FF=36,RAM_bits=0),whole_FIT=False,STA=False,P2_selected=False,full_RUN=False,physical60fps=False,evidence_hashes=pins)
 (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
 with (out/'costs.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
 print(json.dumps(dict(passed=True,pins=len(pins),runs=len(rows),areas=areas)))

if __name__=='__main__':main()
