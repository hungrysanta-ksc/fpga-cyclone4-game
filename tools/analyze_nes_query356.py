# SPDX-License-Identifier: MIT
"""Actual query/source replacement: same-phase timing and whole Lite cost."""
import json,csv,re,argparse
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_execute334 import wire
from analyze_nes_receipt335 import completed_unit,load_image

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=BASE/'probes/nes-query356');a=ap.parse_args();pins={}
 def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
 def js(p):return json.loads(read(p))
 baseline=js(ROOT/'analysis/raster355-verification.json');runs={}
 for tag,oldtag in [('window04','window01'),('fixed01','fixed01'),('normal01','normal01')]:
  d=a.root/tag;b=BASE/'probes/nes-raster355'/oldtag
  r=js(d/'result.json');br=js(b/'result.json');assert r['passed']
  for n,h in r['rtl_hashes'].items():assert sha(d/n)==h;read(d/n)
  assert load_image(d/'output.elf')==load_image(b/'output.elf');read(d/'output.elf') if False else None
  pins[str(d/'output.elf')]=sha(d/'output.elf')
  assert 'PASS REFILL267 frames=3' in read(d/'vsim.log')
  assert 'Errors: 0, Warnings: 0' in read(d/'vlog.log')
  read(d/'joint266_tb.sv');ev=list(csv.reader(read(d/'joint-events.csv').splitlines()))
  cycles={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(read(d/'cycles.csv').splitlines())};rows=[]
  for prev in baseline['runs'][oldtag]['rows']:
   f=prev['frame'];events=[x for x in ev if len(x)>1 and x[1]==str(f)];first=lambda n:next(x for x in events if x[0]==n)
   start=first('start319');end=first('frame_done');req=next(x for x in events if x[0]=='firstreq305' and x[2]=='0');accept=next(x for x in events if x[0]=='rom_accept327' and x[2]=='0')
   startms=int(start[2])/1e9;requestms=int(req[-1])/1e9;acceptms=int(accept[-1])/1e9
   if tag=='fixed01':assert startms==prev['start_ms'] and int(start[3])==prev['start_ROM_cycle']
   assert wire(js(d/f'arm{f}.json')['transfers'])==wire(js(b/f'arm{f}.json')['transfers'])
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
   assert int(first('display266')[2])==12*(f-904)
   credit=max(int(x[2]) for x in events if x[0]=='credits');assert credit<=2
   arm=next(x for x in r['ARM']['frames'] if x['frame']==f);ba=next(x for x in br['ARM']['frames'] if x['frame']==f)
   srcwire=[x for x in events if x[0]=='input_wire337']
   baseline_ev=list(csv.reader(read(b/'joint-events.csv').splitlines()))
   basesrc=[x for x in baseline_ev if x[0]=='input_wire337' and x[1]==str(f)]
   source_bytes=sum(int(x[5]) for x in srcwire);base_source_bytes=sum(int(x[5]) for x in basesrc)
   empty=sum(x[3]=='0' and x[4]=='0' for x in srcwire);base_empty=sum(x[3]=='0' and x[4]=='0' for x in basesrc)
   inputdone=first('input_done337');bi=next(x for x in baseline_ev if x[0]=='input_done337' and x[1]==str(f))
   latency=[(int(x[4])-int(x[3]))/1000 for x in events if x[0]=='query356']
   legacy_total=cycles[f]+int(end[3])/1e9
   total=(int(end[2])-int(start[2]))/1e9
   bev=list(csv.reader(read(b/'joint-events.csv').splitlines()))
   bs=next(x for x in bev if x[0]=='start319' and x[1]==str(f));be=next(x for x in bev if x[0]=='frame_done' and x[1]==str(f))
   basewall=(int(be[2])-int(bs[2]))/1e9
   rows.append(dict(frame=f,total_ms=total,baseline_ms=basewall,delta_ms=total-basewall,legacy_total_ms=legacy_total,unaccounted_handshake_ms=total-legacy_total,gap_ms=total-1000/60,start_ms=startms,start_ROM_cycle=int(start[3]),start_delta_ms=startms-prev['start_ms'],request_relative_ms=requestms-startms,request_advance_ms=prev['request_relative_ms']-(requestms-startms),accept_relative_ms=acceptms-startms,post_ROM_ms=int(end[2])/1e9-acceptms,instructions=arm['instructions'],instruction_delta=arm['instructions']-ba['instructions'],SPI_bytes=arm['SPI_bytes'],SPI_delta=arm['SPI_bytes']-ba['SPI_bytes'],max_credit=credit,qualified_units=len(actual),published_chunks=published,wire_exact=True,source_SPI_bytes=source_bytes,source_SPI_delta=source_bytes-base_source_bytes,empty_source_polls=empty,baseline_empty_source_polls=base_empty,input_end_relative_ms=(int(inputdone[-1])-int(start[2]))/1e9,input_end_delta_ms=(int(inputdone[-1])-int(start[2])-int(bi[-1])+int(bs[2]))/1e9,query_count=len(latency),query_latency_ns=[min(latency),max(latency)] if latency else None))
  runs[tag]=dict(rows=rows,IRQ_cases=len(r['ARM']['IRQ_cases']))
 m=js(a.root/'map01/result.json');assert m['passed']
 for n,h in m['actual_inputs'].items():assert sha(a.root/'map01'/n)==h;read(a.root/'map01'/n)
 for n in ('nes_core257.sv','nes_joint257.sv','nes_transport257.sv'):
  assert [x for x in read(a.root/'map01'/n).splitlines() if x.strip()]==[x for x in read(a.root/'fixed01'/n).splitlines() if x.strip()],n # inherited map generator has one extra blank line
 summary=read(a.root/'map01/output_files/board.map.summary');read(a.root/'map01/output_files/board.map.rpt')
 whole={k:int(re.search(p+r'\s*:\s*([0-9,]+)',summary)[1].replace(',','')) for k,p in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Total registers'),('RAM_bits','Total memory bits')]}
 own={}
 for line in read(a.root/'map01/output_files/board.map.rpt').splitlines():
  fields=[x.strip() for x in line.split(';')]
  if len(fields)>12 and re.fullmatch(r'\d+ \(\d+\)',fields[2]):own[fields[10]]=int(re.search(r'\((\d+)\)',fields[2])[1])
 assert sum(own.values())==whole['comb']
 oldown=js(ROOT/'analysis/ingress338-verification.json')['own_entity_comb']
 own_delta={k:own.get(k,0)-oldown.get(k,0) for k in sorted(set(own)|set(oldown)) if own.get(k,0)!=oldown.get(k,0)}
 for folder in ('guards01','guards02','guards03','guards04'):
  read(a.root/folder/'joint266_tb.sv')
  for n,h in js(a.root/'fixed01/result.json')['rtl_hashes'].items():assert sha(a.root/folder/n)==h
 cases=[]
 for case in (1,3,5,6,7,24,25,26):
  folder='guards04' if case==26 else 'guards02' if case==25 else 'guards01'
  p=a.root/folder/('case'+str(case))/'vsim.log';log=read(p)
  failure=None
  if case==24:
   assert '** Fatal: query not drained356' in log and 'PASS OWNER319' not in log
   failure='collector release suppresses response; bridge WAIT cannot drain'
  elif case==26:
   assert '** Fatal: source DONE after STOP356' in log and 'PASS OWNER319' not in log
   failure='queued source DONE is published after STOP during lease handoff'
  else:assert f'PASS OWNER319 GUARD={case}' in log
  cases.append(dict(case=case,passed=failure is None,log_sha256=sha(p),failure=failure))
 guards=dict(passed=False,cases=cases,passed_cases=6,failed_cases=2,failed_case_numbers=[24,26])
 for folder in ('aperture','final-raw0'):
  assert js(a.root/'guards03'/folder/'result.json')['passed'];read(a.root/'guards03'/folder/'vsim.log')
 for name in ('nes_query356.py','probe_nes_query356.py','guard_nes_query356.py','map_nes_query356.py','analyze_nes_query356.py','nes_query355.sv'):read(ROOT/'tools'/name)
 profile=js(BASE/'probes/nes-raster355/profile01/result.json')['rows'][-1]
 result=dict(stage=356,passed=False,analysis_passed=True,normal_schedules_passed=True,STOP_drain_passed=False,selected_RTL=338,selected_ARM=355,candidate_selected=False,runs=runs,whole=whole,own_entity_delta=own_delta,whole_delta={k:whole[k]-baseline['whole'][k] for k in whole},comb_deficit=whole['comb']-15408,selected_comb_deficit=1866,guards=guards,ARM_profile_reused=profile,compact_row_H2_max_removal_ms=(32548+12518)/84000,new_integrated_RTL=True,new_whole_MAP=True,FIT=False,STA=False,scope='Actual collector/source and M4 instructions at CPI1/84MHz with SPI/IRQ/2slots/staging/ROM. Retained ordinary65816 trace, map/tile/display busmodel. Not fullRUN/full65816/physicalWCET/60fps. Candidate rejected: whole combinational cost regresses, normal-ROM time regresses and actual collector release cancels a reply while query WAIT assumes eventual response, and queued source DONE is not suppressed by STOP.',pins=pins)
 (ROOT/'analysis/query356-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
 print(json.dumps(dict(warm={k:v['rows'][-1] for k,v in runs.items()},whole=whole,delta=result['whole_delta'],pins=len(pins)),indent=2))
if __name__=='__main__':main()
