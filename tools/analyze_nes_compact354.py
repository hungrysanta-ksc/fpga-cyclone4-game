# SPDX-License-Identifier: MIT
"""Same-phase and continuous whole-cost comparison, actual read/ACK invariants."""
import argparse,csv,json
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile
from analyze_nes_execute334 import wire
from analyze_nes_receipt335 import completed_unit,load_image

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=BASE/'probes/nes-compact354');ap.add_argument('--partial',action='store_true');a=ap.parse_args();pins={}
 def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
 def js(p):return json.loads(read(p))
 prior=js(ROOT/'analysis/raw352-verification.json');boundary=js(ROOT/'analysis/boundary353-verification.json')
 if not a.partial:
  for p,h in boundary['pins'].items():assert sha(Path(p))==h,p;pins[p]=h
 runs={};image=None
 for tag,ref in [('window01','window02'),('fixed01','fixed02'),('normal01','normal02')]:
  d=a.root/tag;b=BASE/'probes/nes-raw352'/ref
  if not (d/'result.json').exists():assert a.partial;continue
  r=js(d/'result.json');br=js(b/'result.json');assert r['passed'] and r['rtl_hashes']==br['rtl_hashes']
  for n,h in r['rtl_hashes'].items():assert sha(d/n)==h;read(d/n)
  for n in ('blocks.txt','CPU-bus.csv','CPU-timing.csv','CPU-ordinary.sfc','source-cost280.hex','transaction-cost280.hex','control280.hex','source-ARM-decoder.elf','nes_decode280.c'):
   assert sha(d/n)==sha(b/n),(tag,n);pins[str(d/n)]=sha(d/n)
  assert sha(d/'output.elf')==r['ELF_sha256'];pins[str(d/'output.elf')]=sha(d/'output.elf')
  for name in ('nes_input286.inc','nes_planner211.c','nes_native165.h','nes_delta231.c'):read(d/name)
  assert sha(d/'joint266_tb.sv')==r['tb_sha256'];read(d/'joint266_tb.sv')
  if image is None:image=load_image(d/'output.elf')
  else:assert image==load_image(d/'output.elf')
  assert 'Errors: 0, Warnings: 0' in read(d/'vlog.log');assert 'PASS REFILL267 frames=3' in read(d/'vsim.log')
  ev=list(csv.reader(read(d/'joint-events.csv').splitlines()));cycles={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(read(d/'cycles.csv').splitlines())};rows=[]
  for prev in prior['runs'][ref]['rows']:
   f=prev['frame'];events=[x for x in ev if len(x)>1 and x[1]==str(f)];first=lambda name:next(x for x in events if x[0]==name)
   start=first('start319');end=first('frame_done');req=next(x for x in events if x[0]=='firstreq305' and x[2]=='0');accept=next(x for x in events if x[0]=='rom_accept327' and x[2]=='0')
   startms=int(start[2])/1e9;requestms=int(req[-1])/1e9;acceptms=int(accept[-1])/1e9
   if tag=='fixed01':assert startms==prev['start_ms'] and int(start[3])==prev['start_ROM_cycle']
   arm=next(x for x in r['ARM']['frames'] if x['frame']==f);ba=next(x for x in br['ARM']['frames'] if x['frame']==f)
   assert wire(js(d/f'arm{f}.json')['transfers'])==wire(js(b/f'arm{f}.json')['transfers']),(tag,f,'output order/material')
   expected=[];actual=[];offset=0;token=None;writes=[];published=0
   for x in events:
    if x[0]=='read336':
     tok,op,section,pos,off,data,t=map(int,x[2:]);assert off==offset
     if not offset:token=tok
     assert token==tok;offset+=1;u=completed_unit(op,section,pos,2)
     if u:expected.append((tok,int(u[0]),u[1]))
    elif x[0]=='unit336':actual.append(tuple(map(int,x[2:5])))
    elif x[0]=='private336':
     tok,addr,value,t=map(int,x[2:]);assert tok==token;writes.append(t)
    elif x[0]=='publish336':
     tok,n,t=map(int,x[2:]);assert tok==token and n==offset and n>0 and all(z<t for z in writes)
     offset=0;token=None;writes=[];published+=1
   assert expected==actual and offset==0
   display=first('display266');assert int(display[2])==12*(f-904)
   credit=max(int(x[2]) for x in events if x[0]=='credits');assert credit<=2
   total=cycles[f]+int(end[3])/1e9
   rows.append(dict(frame=f,total_ms=total,baseline_ms=prev['total_ms'],delta_ms=total-prev['total_ms'],gap_ms=total-1000/60,start_ms=startms,start_ROM_cycle=int(start[3]),start_delta_ms=startms-prev['start_ms'],request_relative_ms=requestms-startms,request_advance_ms=prev['request_relative_ms']-(requestms-startms),accept_relative_ms=acceptms-startms,post_ROM_ms=int(end[2])/1e9-acceptms,instructions=arm['instructions'],instruction_delta=arm['instructions']-ba['instructions'],components=arm['components'],baseline_components=ba['components'],SPI_bytes=arm['SPI_bytes'],SPI_delta=arm['SPI_bytes']-ba['SPI_bytes'],max_credit=credit,qualified_units=len(actual),published_chunks=published,wire_exact=True))
  with (d/'output.elf').open('rb') as fp:
   elf=ELFFile(fp);sizes={n:elf.get_section_by_name(n)['sh_size'] if elf.get_section_by_name(n) else 0 for n in ('.text','.bss','.data')}
  runs[tag]=dict(rows=rows,sizes=sizes,stack=r['ARM']['stack_observed'],IRQ_cases=len(r['ARM']['IRQ_cases']))
 if a.partial:print(json.dumps(runs,indent=2));return
 guards=js(a.root/'guards03/result.json');assert guards['passed'] and len(guards['rows'])==71 and len(guards['negative_cases'])==13
 lifetime=js(a.root/'lifetime01/result.json');assert lifetime['passed']
 for evidence in (guards,lifetime):
  stable={};temp=Path('C:/Users/mohallo/AppData/Local/Temp/nes-compact354')
  for p,h in evidence['pins'].items():
   q=Path(p)
   if q.is_relative_to(temp):q=a.root/q.relative_to(temp)
   assert sha(q)==h;stable[str(q)]=h;pins[str(q)]=h
  evidence['pins']=stable
 assert image==load_image(a.root/'build01/output.elf'),'guard build differs from full schedule image'
 for n in ('nes_compact354.py','probe_nes_compact354.py','check_nes_compact354.py','analyze_nes_compact354.py'):read(ROOT/'tools'/n)
 whole=prior['whole'];assert whole['comb']==17274
 result=dict(stage=354,passed=True,runs=runs,guards=guards,lifetime=lifetime,whole=whole,comb_deficit=1866,whole_delta=dict(LE=0,comb=0,FF=0,RAM_bits=0),new_MAP=False,unchanged_RTL_MAP_reused=True,budget=prior['budget'],scope='Actual M4 instructions with CPI1/84MHz, live SPI/IRQ/2slots/staging/ROM and retained SNES trace. No full firmwareRUN, full65816, physicalWCET/FPS, newRTL/FIT/STA.71 preparation cases are not71 full schedules.',pins=pins)
 (ROOT/'analysis/compact354-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
 print(json.dumps(dict(passed=True,warm={k:v['rows'][-1] for k,v in runs.items()},whole=whole,pins=len(pins)),indent=2))
if __name__=='__main__':main()
