# SPDX-License-Identifier: MIT
"""NES348 separate source/control whole-cost and schedule verification."""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_decode280 import records,chunks
from analyze_nes_receipt335 import completed_unit,load_image
from analyze_nes_execute334 import wire
from probe_nes_arm264 import ELFFile

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');a=ap.parse_args()
 root=BASE/'probes/nes-fixed348';pins={}
 def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
 def js(p):return json.loads(read(p))
 baseline=js(ROOT/'analysis/ingress338-verification.json')
 for p,h in baseline['pins'].items():assert sha(Path(p))==h;pins[p]=h
 runs={}
 for tag,ref,source in [('source02','window03',True),('fixed01','fixed01',True),('normal01','normal01',True),('control02','window03',False),('control-fixed01','fixed01',False),('control-normal01','normal01',False)]:
  d=root/tag
  if not (d/'result.json').exists():assert a.partial,tag;continue
  r=js(d/'result.json');assert r['passed']
  for n,h in r['rtl_hashes'].items():assert sha(d/n)==h;read(d/n)
  for n,h in r['input_hashes'].items():
   p=Path(n) if Path(n).is_absolute() else BASE/n if n.startswith(('probes/','repository-nes-milestone/')) else d/n
   if not p.is_file() or sha(p)!=h:p=ROOT/'tools'/Path(n).name
   assert p.is_file() and sha(p)==h,(tag,n)
   pins[str(p)]=h
  assert sha(d/'output.elf')==r['ELF_sha256'];pins[str(d/'output.elf')]=sha(d/'output.elf')
  assert sha(d/'joint266_tb.sv')==r['tb_sha256'];read(d/'joint266_tb.sv')
  assert 'Errors: 0, Warnings: 0' in read(d/'vlog.log')
  assert 'PASS REFILL267 frames=3' in read(d/'vsim.log')
  if source:assert sha(d/'nes_decode280.c')==js(BASE/'probes/nes-fixed347/arm01/result.json')['C_sha256']
  else:assert load_image(d/'output.elf')==load_image(BASE/f'probes/nes-ingress338/{ref}/output.elf')
  for n in ('CPU-bus.csv','CPU-timing.csv','CPU-ordinary.sfc'):
   assert sha(d/n)==sha(BASE/f'probes/nes-ingress338/{ref}'/n);pins[str(d/n)]=sha(d/n)
  ev=list(csv.reader(read(d/'joint-events.csv').splitlines()));blocks=read(d/'blocks.txt').splitlines()
  cycles={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(read(d/'cycles.csv').splitlines())};rows=[]
  for prev in baseline['runs'][ref]['rows']:
   f=prev['frame'];events=[x for x in ev if len(x)>1 and x[1]==str(f)]
   first=lambda n:next(x for x in events if x[0]==n)
   start=first('start319');end=first('frame_done');request=next(x for x in events if x[0]=='firstreq305' and x[2]=='0');accept=next(x for x in events if x[0]=='rom_accept327' and x[2]=='0')
   total=cycles[f]+int(end[3])/1e9;startms=int(start[2])/1e9;endms=int(end[2])/1e9
   if 'fixed' in tag:assert startms==prev['start_ms'] and int(start[3])==prev['start_ROM_cycle']
   expected_path=BASE/f'probes/nes-fixed347/arm01/frame{f}.records' if source else BASE/f'probes/nes-ingress338/{ref}/frame{f}.records'
   rr=records(d/f'frame{f}.records');expected=records(expected_path);assert rr==expected
   actual=[bytes.fromhex(x.split()[3]) for x in blocks if x.split()[0]==str(f)];assert actual==chunks(expected)
   read(d/f'frame{f}.records');read(expected_path)
   arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
   transfers=js(d/f'arm{f}.json')['transfers'];oldwire=wire(js(BASE/f'probes/nes-ingress338/{ref}/arm{f}.json')['transfers'])
   assert wire(transfers)==oldwire,(tag,f,'output packet material/order')
   expected_units=[];observed=[];offset=0;token=None;writes=[];published=0
   for x in events:
    if x[0]=='read336':
     tok,op,section,pos,off,data,t=map(int,x[2:]);assert off==offset
     if not offset:token=tok
     assert token==tok;offset+=1;u=completed_unit(op,section,pos,2)
     if u:expected_units.append((tok,int(u[0]),u[1]))
    elif x[0]=='unit336':observed.append(tuple(map(int,x[2:5])))
    elif x[0]=='private336':
     tok,addr,value,t=map(int,x[2:]);assert tok==token;writes.append(t)
    elif x[0]=='publish336':
     tok,n,t=map(int,x[2:]);assert token==tok and n==offset and n>0 and all(z<t for z in writes)
     token=None;offset=0;writes=[];published+=1
   assert expected_units==observed and offset==0
   credit=max(int(x[2]) for x in events if x[0]=='credits');assert credit<=2
   inputs=[x for x in events if x[0]=='input_ARM340']
   if source:assert arm['decoder_excluded']==0 and len(inputs)==len(actual)
   rows.append(dict(frame=f,total_ms=total,delta_ms=total-prev['total_ms'],start_ms=startms,start_delta_ms=startms-prev['start_ms'],start_ROM_cycle=int(start[3]),source_ms=cycles[f],first_request_relative_ms=int(request[-1])/1e9-startms,first_accept_relative_ms=int(accept[-1])/1e9-startms,post_ROM_ms=endms-int(accept[-1])/1e9,gap_ms=total-1000/60,payload=sum(map(len,actual)),banks=len(actual),successful_source_wire=sum(map(len,actual))+15*len(actual)+8,ARM_instructions=arm['instructions'],output_SPI_bytes=arm['SPI_bytes'],max_credit=credit,qualified_units=len(observed),published_chunks=published))
  with (d/'output.elf').open('rb') as fp:
   elf=ELFFile(fp);sizes={n:elf.get_section_by_name(n)['sh_size'] if elf.get_section_by_name(n) else 0 for n in ('.text','.data','.bss')}
  runs[tag]=dict(rows=rows,sizes=sizes,stack=r['ARM']['stack_observed'],IRQ_cases=len(r['ARM']['IRQ_cases']))
 boards={}
 for tag,run in [('map-source01','source02'),('map-control02','control02')]:
  d=root/tag
  if not (d/'result.json').exists():assert a.partial;continue
  r=js(d/'result.json');assert r['passed']
  for n,h in r['actual_inputs'].items():assert sha(d/n)==h;read(d/n)
  for n in ('nes_core257.sv','nes_queue260.sv','nes_spi270.sv','nes_plan_spi200.sv','nes_plan_batch206.sv'):
   assert sha(d/n)==sha(root/run/n),(tag,n,'board versus measured RTL')
  host=read(d/'nes_mux260.sv').replace(' output wire tile_closed267,\n','').replace('reg tiles_closed;assign tile_closed267=tiles_closed;','reg tiles_closed;')
  assert host==read(root/run/'nes_mux260.sv')
  log=read(d/'map.log');assert 'Warning (10034)' not in log
  assert all('cache_index141' in x for x in re.findall(r'Warning \(10240\):[^\r\n]+',log))
  whole={k:int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',r['summary'])[1].replace(',','')) for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
  report=read(d/'output_files/board.map.rpt');nodes={}
  for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
   c=[x.strip() for x in line.split(';')]
   if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):nodes[c[10]]=int(re.search(r'\((\d+)\)',c[2])[1])
  assert sum(nodes.values())==whole['comb']
  boards[tag]=dict(whole=whole,delta={k:whole[k]-baseline['whole'][k] for k in whole},comb_deficit=whole['comb']-15408,entity_own_comb=nodes)
 for n in ('nes_fixed348.py','nes_control348.py','nes_plan348.py','probe_nes_fixed348.py','probe_nes_control348.py','check_nes_source348.py','check_nes_plan348.py','map_nes_fixed348.py','guard_nes_control348.py','guard_nes_fixed348.py','check_nes_bg348.py','analyze_nes_fixed348.py'):read(ROOT/'tools'/n)
 guards={}
 for name in ('directed03','plan07','armguards01','guards02','sourceguards01'):
  p=root/name/'result.json'
  if not p.exists():assert a.partial,name;continue
  g=js(p);assert g['passed'];guards[name]=g
  if name=='directed03':assert g['RTL_sha256']==sha(root/'source02/nes_core257.sv')
  if name=='plan07':
   assert g['RTL_sha256']==sha(root/'control02/nes_plan_batch206.sv')
   assert g['plans']==708 and g['alt_masks']==256 and g['clear_STOP'] and g['malformed']==list(range(1,9))
  for p in (root/name).rglob('*'):
   if p.is_file() and p.suffix in ('.sv','.log','.txt','.hex') and 'work' not in p.parts:pins[str(p)]=sha(p)
  if name=='armguards01':assert g['ELF_sha256']==sha(root/'source02/output.elf')
  if name in ('guards02','sourceguards01'):
   run='control02' if name=='guards02' else 'source02'
   assert g['ELF_sha256']==sha(root/run/'output.elf')
   assert g['rtl_hashes']==js(root/run/'result.json')['rtl_hashes']
   assert {x['case'] for x in g['cases']}==({29} if name=='guards02' else {1,5,6})
   for case in g['cases']:
    p=root/name/f"case{case['case']}/vsim.log";assert sha(p)==case['log_sha256'];read(p)
   for sub in ('final-raw0','aperture'):assert js(root/name/sub/'result.json')['passed']
 oldguards=root/'guards01'
 if oldguards.exists():
  completed=[]
  for case in (2,3,4,5,6,7,11,12,18,20,23):
   p=oldguards/f'case{case}/vsim.log'
   if not p.exists():assert a.partial;continue
   log=read(p);assert f'PASS OWNER319 GUARD={case}' in log and 'Errors: 0' in log
   assert not re.search(r'\*\* (Error|Fatal):',log)
   completed.append(case)
  for n,h in js(root/'control02/result.json')['rtl_hashes'].items():assert sha(oldguards/n)==h;read(oldguards/n)
  oldtb=read(oldguards/'joint266_tb.sv')
  if (root/'guards02/joint266_tb.sv').exists():
   corrected=oldtb.replace('begin #(NEG319==10?200000000:100000);','begin #(NEG319==10?200000000:NEG319==29?1000000:100000);')
   corrected=corrected.replace('  disable fork;\n  repeat(8)','  disable fork;\n  if(NEG319==29&&!spi_front270.ss[1])$fatal(1,"length fault before transaction end348");\n  repeat(8)')
   assert corrected==read(root/'guards02/joint266_tb.sv')
  log=read(oldguards/'case29/vsim.log');assert 'missing expected fault319' in log
  req=[]
  for p in (oldguards/'case29').glob('arm-req*'):
   v=p.read_text().split()
   if len(v)>3 and v[3]=='e1':req.append((p,int(v[0])))
  assert req and req[0][1]==51;read(req[0][0])
  guards['control_completed_before_timeout']=dict(original_suite_passed=False,completed_cases=completed,failed_case=29,reason='100us deadline expired before end of51B E1 transaction injected atbyte15; only29 rerun, others retained',remaining_wire_lower_ms=(51-15)*8/2625000*1000)
 else:assert a.partial
 from analyze_nes_order343 import plans
 plan_path=root/'control02/actual-plans293-907.bin'
 pp=plans(plan_path);pins[str(plan_path)]=sha(plan_path)
 assert [(x[0],len(x[2])) for x in pp[:2]]==[(2,3),(0,7)]
 first_plan_extra=64-sum(len(x[2]) for x in pp[:2]);assert first_plan_extra==54
 first_plan_cost=dict(extra_bytes=first_plan_extra,extra_NES_clocks=first_plan_extra*2,arithmetic_ms=first_plan_extra*2*45.454/1e6)
 if 'control-fixed01' in runs:
  events=list(csv.reader(read(BASE/'probes/nes-ingress338/fixed01/joint-events.csv').splitlines()))
  at=int(next(x[2] for x in events if x[0]=='start319' and x[1]=='907'))
  req=int(next(x[-1] for x in events if x[0]=='firstreq305' and x[1]=='907' and x[2]=='0'))
  observed=runs['control-fixed01']['rows'][-1]['first_request_relative_ms']-(req-at)/1e9
  first_plan_cost['observed_first_request_delta_ms']=observed
  assert abs(observed-first_plan_cost['arithmetic_ms'])<0.000002
 out=dict(first_plan_cost=first_plan_cost,stage=348,passed=True,complete=not a.partial,selected_RTL=338,selected_ARM=336,selected_gap_ms=4.022994145333332,selected_comb_deficit=1866,new_RTL=True,new_ARM=True,new_MAP=True,runs=runs,boards=boards,guards=guards,baseline_pins_rehashed=len(baseline['pins']),scope='Separate actual M4/SPI/IRQ/2slot/ROM schedules; CPI1 and IRQ allocations, retained65816 trace and C map/tile model. No physical WCET/fullRUN/FIT/STA. No combined candidate measurement; do not add isolated area/time deltas.',pins=pins)
 if not a.partial:(ROOT/'analysis/fixed348-verification.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n')
 compact={**out,'boards':{k:{q:v for q,v in b.items() if q!='entity_own_comb'} for k,b in boards.items()}}
 print(json.dumps({k:v for k,v in compact.items() if k!='pins'},indent=2))
if __name__=='__main__':main()
