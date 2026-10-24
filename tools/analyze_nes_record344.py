# SPDX-License-Identifier: MIT
"""NES344 actual schedule and source-record replacement ledger."""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_receipt335 import load_image,completed_unit
from analyze_nes_execute334 import wire
from probe_nes_arm264 import ELFFile

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');o=ap.parse_args();root=BASE/'probes/nes-record344';pins={}
 def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
 def js(p):return json.loads(read(p))
 baseline=js(ROOT/'analysis/ingress338-verification.json');oldrtl=js(BASE/'probes/nes-ingress338/window03/result.json')['rtl_hashes'];runs={}
 for tag,ref in [('rtl01','window03'),('arm01','window03'),('joint01','window03'),('service01','window03'),('servicefixed01','fixed01'),('servicenormal01','normal01')]:
  d=root/tag
  if not (d/'result.json').exists():assert o.partial,tag;continue
  r=js(d/'result.json');assert r['passed'];changes={n for n,h in r['rtl_hashes'].items() if h!=oldrtl[n]};assert changes==(set() if tag=='arm01' else {'nes_core257.sv'})
  for n,h in r['rtl_hashes'].items():assert sha(d/n)==h;read(d/n)
  for n,h in r['input_hashes'].items():
   p=Path(n) if Path(n).is_absolute() else BASE/n if n.startswith(('probes/','repository-nes-milestone/')) else d/n
   if not p.is_file() or sha(p)!=h:
    original=ROOT/'tools'/Path(n).name
    assert original.is_file() and sha(original)==h,(tag,n);p=original
   pins[str(p)]=h
  assert sha(d/'joint266_tb.sv')==r['tb_sha256'];read(d/'joint266_tb.sv');assert sha(d/'output.elf')==r['ELF_sha256'];pins[str(d/'output.elf')]=sha(d/'output.elf')
  if tag=='rtl01':assert load_image(d/'output.elf')==load_image(BASE/'probes/nes-ingress338/window03/output.elf')
  else:assert load_image(d/'output.elf')==load_image(root/('service01' if tag.startswith('service') else 'arm01')/'output.elf')
  for code in d.iterdir():
   if code.is_file() and code.suffix in ('.c','.h','.inc'):read(code)
  assert 'Errors: 0, Warnings: 0' in read(d/'vlog.log') and 'PASS REFILL267 frames=3' in read(d/'vsim.log')
  for n in ('CPU-bus.csv','CPU-timing.csv','CPU-ordinary.sfc','source-ARM-decoder.elf','source-ARM-blocks.csv'):
   assert sha(d/n)==sha(BASE/'probes/nes-ingress338'/ref/n);pins[str(d/n)]=sha(d/n)
  assert read(d/'blocks.txt')==read(BASE/'probes/nes-ingress338'/ref/'blocks.txt')
  events=list(csv.reader(read(d/'joint-events.csv').splitlines()));cycles={int(x['frame']):x for x in csv.DictReader(read(d/'cycles.csv').splitlines())};marks=js(d/'metadata317.json');rows=[]
  for prev in baseline['runs'][ref]['rows']:
   f=prev['frame'];assert read(d/f'frame{f}.records')==read(BASE/'probes/nes-ingress338'/ref/f'frame{f}.records')
   e=[x for x in events if len(x)>1 and x[1]==str(f)];first=lambda name:next(x for x in e if x[0]==name)
   start=first('start319');end=first('frame_done');req=next(x for x in e if x[0]=='firstreq305' and x[2]=='0');accept=next(x for x in e if x[0]=='rom_accept327' and x[2]=='0');total=int(cycles[f]['total'])*45.454/1e6+int(end[3])/1e9
   if tag in ('fixed01','servicefixed01'):assert int(start[2])/1e9==prev['start_ms'] and int(start[3])==prev['start_ROM_cycle']
   transfers=js(d/f'arm{f}.json')['transfers'];oldtrans=js(BASE/'probes/nes-ingress338'/ref/f'arm{f}.json')['transfers'];w=wire(transfers);ow=wire(oldtrans);newplans=w.pop(0xe9);oldplans=ow.pop(0xe9);assert w==ow,(tag,f,'E1/DMA')
   def payload(plans):return b''.join((lambda b:b[4:4+int.from_bytes(b[1:3],'little')])(bytes.fromhex(x)) for x in plans)
   assert payload(newplans)==payload(oldplans),(tag,f,'plan order')
   expected=[];observed=[];offset=0;token=None;writes=[];pub=0
   for x in e:
    if x[0]=='read336':
     tok,op,section,pos,off,data,t=map(int,x[2:]);assert off==offset
     if not offset:token=tok
     assert token==tok;offset+=1;u=completed_unit(op,section,pos,2)
     if u:expected.append((tok,int(u[0]),u[1]))
    elif x[0]=='unit336':observed.append(tuple(map(int,x[2:5])))
    elif x[0]=='private336':
     tok,addr,value,t=map(int,x[2:]);assert tok==token;writes.append(t)
    elif x[0]=='publish336':
     tok,n,t=map(int,x[2:]);assert token==tok and n==offset and n>0 and all(z<t for z in writes);offset=0;token=None;writes=[];pub+=1
   assert expected==observed and offset==0
   credit=max(int(x[2]) for x in e if x[0]=='credits');assert credit<=2
   calls=[x for x in marks if x['name']=='advance344' and x['start']['generation']==f-904];prefix=next((x for x in calls if x['end'].get('prefixes344',0)>x['start'].get('prefixes344',0)),None)
   rows.append(dict(frame=f,total_ms=total,delta_ms=total-prev['total_ms'],start_ms=int(start[2])/1e9,start_delta_ms=int(start[2])/1e9-prev['start_ms'],start_ROM_cycle=int(start[3]),source_cycles=cycles[f],first_request_ms=int(req[-1])/1e9,first_request_after_start_ms=(int(req[-1])-int(start[2]))/1e9,first_accept_ms=int(accept[-1])/1e9,first_OBJ_request_ms=int(next(x for x in e if x[0]=='firstreq305' and x[2]=='1')[-1])/1e9,post_ROM_ms=(int(end[2])-int(accept[-1]))/1e9,gap_ms=total-1000/60,first_E9_wire=len(bytes.fromhex(newplans[0])),plan_wire=sum(len(bytes.fromhex(x)) for x in newplans),output_SPI_bytes=sum(len(x['tx'])//2 for x in transfers),E2_responses=sum(x['tx'].startswith('e2') for x in transfers),E9_packets=len(newplans),advance_calls=len(calls),advance_instructions=sum(x['end']['instruction']-x['start']['instruction'] for x in calls),prefix_timing=prefix,qualified_units=len(observed),published_chunks=pub,max_credit=credit))
  with (d/'output.elf').open('rb') as fp:
   elf=ELFFile(fp);sizes={n:elf.get_section_by_name(n)['sh_size'] if elf.get_section_by_name(n) else 0 for n in ('.text','.data','.bss')}
  runs[tag]=dict(rows=rows,sizes=sizes,stack=r['ARM']['stack_observed'],IRQ_cases=len(r['ARM']['IRQ_cases']))
 boards={};d=root/'map01'
 if (d/'result.json').exists():
  r=js(d/'result.json');assert r['passed'];old=js(BASE/'probes/nes-ingress338/board01/result.json');assert {n for n,h in r['actual_inputs'].items() if h!=old['actual_inputs'].get(n)}=={'nes_core257.sv'}
  for n,h in r['actual_inputs'].items():assert sha(d/n)==h;read(d/n)
  log=read(d/'map.log');assert 'Warning (10034)' not in log;assert all('cache_index141' in x for x in re.findall(r'Warning \(10240\):[^\r\n]+',log))
  whole={k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',r['summary'])[1].replace(',','')) for k,v in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
  nodes={};report=read(d/'output_files/board.map.rpt')
  for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
   c=[x.strip() for x in line.split(';')]
   if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):nodes[c[10]]=int(re.search(r'\((\d+)\)',c[2])[1])
  assert sum(nodes.values())==whole['comb']
  assert any('State Machine - ' in line and 'nes_core257:encoder|state' in line for line in report.splitlines())
  boards=dict(whole=whole,delta={k:whole[k]-baseline['whole'][k] for k in whole},comb_deficit=whole['comb']-15408,own={k:v for k,v in nodes.items() if k.endswith(('nes_output260:flow','nes_core257:encoder'))})
  if 'joint01' in runs:assert read(d/'nes_core257.sv')==read(root/'joint01/nes_core257.sv')
 guards=[]
 if not o.partial:
  for n,h in baseline['pins'].items():assert sha(Path(n))==h
  ag=js(root/'armguards02/result.json');assert ag['passed'] and ag['ELF_sha256']==sha(root/'joint01/output.elf')
  for name in ('serviceguards02','continuation02'):
   sg=js(root/name/'result.json');assert sg['passed'] and sg['ELF_sha256']==sha(root/'service01/output.elf')
  g=js(root/'guards01/result.json');assert g['passed'] and g['rtl_hashes']==js(root/'service01/result.json')['rtl_hashes'] and g['ELF_sha256']==sha(root/'service01/output.elf')
  for x in g['cases']:
   p=root/f"guards01/case{x['case']}/vsim.log";assert sha(p)==x['log_sha256'];read(p);guards.append(x['case'])
  for n,rtl,tb in [('final-raw0','nes_validator278.sv','final332_tb.sv'),('aperture','nes_bulk_aperture188.sv','aperture325_tb.sv')]:
   sub=root/'guards01'/n;rsub=js(sub/'result.json');assert rsub['passed'] and rsub['RTL_sha256']==sha(root/'service01'/rtl)
   for fn,key in [(rtl,'RTL_sha256'),(tb,'tb_sha256'),('vsim.log','log_sha256')]:
    assert sha(sub/fn)==rsub[key];read(sub/fn)
  st=js(root/'source01/result.json');assert st['passed'] and st['SHIFT_counts']==[0,1,1,0] and st['SHIFT_build_STOP']
  assert st['RTL_sha256']==sha(root/'service01/nes_core257.sv')
  for name,key in [('record344_tb.sv','TB_sha256'),('vsim.log','log_sha256'),('stop/vsim.log','stop_log_sha256'),('records.txt','records_sha256')]:
   p=root/'source01'/name;assert sha(p)==st[key];read(p)
  missing=set(re.findall(r"Missing connection for port '([^']+)'",read(root/'source01/vsim.log')))
  assert missing==set('record_flush raw_index raw_query in_offset in_data in_ready in_valid query_generation sink_lane sink_unit sink_kind sink_data sink_valid stream_ready output_phase crc_result context_ready h_ready v_sealed v_ready display_response display_response_valid display_request_ready source_raw278 record_last319 plan_cursor319'.split())
  read(root/'v1-cancel.json')
 for p in ROOT.glob('tools/*344.py'):read(p)
 out=dict(stage=344,passed=True,selected=False,new_RTL=True,new_ARM=True,new_MAP=True,integrated_observations=18,unique_recorded_frames=3,source_directed_frames=4,source_SHIFT_STOP=True,baseline_evidence_rehashed=len(baseline['pins']),selected_RTL=338,selected_ARM=336,selected_gap_ms=4.022994145333332,selected_comb_deficit=1866,cancelled_v1_fixed=True,runs=runs,board=boards,RTL_guards=guards,scope='Actual M4/IRQ/SPI/2slot/ROM RTL with replayed SNES bus trace and CPI allocations; not physical fullRUN/FIT/STA.',pins=pins)
 if not o.partial:(ROOT/'analysis/record344-verification.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n')
 print(json.dumps({k:v for k,v in out.items() if k!='pins'},indent=2))
if __name__=='__main__':main()
