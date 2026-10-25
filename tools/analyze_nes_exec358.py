# SPDX-License-Identifier: MIT
"""Keep338/355: failing six-clock gate, actual collector cancellation repair, prefix timing and whole cost."""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_execute334 import wire
from analyze_nes_receipt335 import completed_unit,load_image

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);a=ap.parse_args();d=a.root.resolve();pins={}
 def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
 def js(p):return json.loads(read(p))
 runs={}
 for mode in ('window01','fixed01'):
  folder=d/mode;b=BASE/'probes/nes-raster355'/mode;r=js(folder/'result.json');assert r['passed'];br=js(b/'result.json')
  for n,h in r['rtl_hashes'].items():assert sha(folder/n)==h;read(folder/n)
  assert load_image(folder/'output.elf')==load_image(b/'output.elf');pins[str(folder/'output.elf')]=sha(folder/'output.elf')
  assert 'PASS REFILL267 frames=3' in read(folder/'vsim.log');read(folder/'joint266_tb.sv')
  ev=list(csv.reader(read(folder/'joint-events.csv').splitlines()));bev=list(csv.reader(read(b/'joint-events.csv').splitlines()));rows=[]
  for f in (905,906,907):
   e=[x for x in ev if x[1]==str(f)];be=[x for x in bev if x[1]==str(f)];get=lambda v,n:next(x for x in v if x[0]==n)
   start=get(e,'start319');end=get(e,'frame_done');bs=get(be,'start319');bend=get(be,'frame_done')
   if mode=='fixed01':assert start[2:]==bs[2:]
   assert wire(js(folder/f'arm{f}.json')['transfers'])==wire(js(b/f'arm{f}.json')['transfers'])
   expected=[];actual=[];offset=0;token=None;writes=[];published=0
   for x in e:
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
   assert expected==actual and offset==0 and int(get(e,'display266')[2])==12*(f-904)
   credit=max(int(x[2]) for x in e if x[0]=='credits');assert credit<=2
   total=(int(end[2])-int(start[2]))/1e9;base=(int(bend[2])-int(bs[2]))/1e9
   rows.append(dict(frame=f,total_ms=total,baseline_ms=base,delta_ms=total-base,start_ROM_cycle=int(start[3]),qualified_units=len(actual),published_chunks=published,max_credit=credit,source_SPI_bytes=sum(int(x[5]) for x in e if x[0]=='input_wire337'),input_ms=(int(get(e,'input_done337')[-1])-int(start[2]))/1e9,wire_exact=True))
  runs[mode]=dict(rows=rows,IRQ_cases=len(r['ARM']['IRQ_cases']))
 guards=js(d/'guards01/result.json');assert guards['passed'] and [r['case'] for r in guards['cases']]==[24,25,26]
 for c in guards['cases']:assert f"PASS OWNER319 GUARD={c['case']}" in read(d/'guards01'/f"case{c['case']}"/'vsim.log')
 for folder in ('aperture','final-raw0'):assert js(d/'guards01'/folder/'result.json')['passed'];read(d/'guards01'/folder/'vsim.log')
 m=js(d/'map01/result.json');assert m['passed']
 for n,h in m['actual_inputs'].items():assert sha(d/'map01'/n)==h;read(d/'map01'/n)
 for n in ('nes_core257.sv','nes_joint257.sv','nes_transport257.sv','nes_native_frame201.sv'):
  assert [x for x in read(d/'map01'/n).splitlines() if x.strip()]==[x for x in read(d/'window01'/n).splitlines() if x.strip()],n
 summary=read(d/'map01/output_files/board.map.summary');read(d/'map01/output_files/board.map.rpt')
 whole={k:int(re.search(p+r'\s*:\s*([0-9,]+)',summary)[1].replace(',','')) for k,p in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Total registers'),('RAM_bits','Total memory bits')]}
 baseline=js(ROOT/'analysis/arch357-verification.json')['budget']['whole_baseline']
 job=js(d/'read03/result.json');assert job['passed'] and not job['six_clock_passed'] and job['max_clocks']==10
 prefix=js(BASE/'probes/nes-exec358/prefix07/result.json');assert prefix['passed']
 for result in (job,prefix):
  for p,h in result['pins'].items():assert sha(Path(p))==h;pins[p]=h
 by_kind={}
 for row in job['jobs']:
  key=f"op{row['op']}_kind{row['kind']}";by_kind[key]=max(by_kind.get(key,0),row['clocks'])
 for n in ('probe_nes_read358.py','nes_cancel358.py','probe_nes_cancel358.py','guard_nes_cancel358.py','map_nes_cancel358.py','analyze_nes_prefix358.py','analyze_nes_exec358.py'):read(ROOT/'tools'/n)
 prefix_summary={k:v for k,v in prefix.items() if k!='rows'};prefix_summary['packet_observations']=len(prefix['rows'])
 result=dict(stage=358,analysis_passed=True,selected_RTL=338,selected_ARM=355,candidate_selected=False,NES_six_clock_passed=False,read_max_clocks=10,read_max_by_kind=by_kind,read_STOP_cases=12,collector_cancel_guards=guards['cases'],runs=runs,cancellation_diagnostic_whole=whole,whole_delta_vs338={k:whole[k]-baseline[k] for k in whole},diagnostic_comb_deficit=whole['comb']-15408,selected_comb_deficit=1866,selected_warm_gap_ms=4.023039333333333,prefix=prefix_summary,new_MAP=True,new_NES_whole_executor=False,FIT=False,STA=False,physical=False,
 scope='338/355 retained. Actual338 extracted read FSM + unchanged validator22MHz bounded fixture fails6cycle gate. Actual collector/DONE repair of rejected host-clock356 separately integrated with actualARM355 and wholeLite. This is not NES common-executor synthesis or safe early-ROM implementation. Same-phase/continuous model, not fullRUN/full65816/VBlank/physicalWCET.',pins=pins)
 (ROOT/'analysis/exec358-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(dict(read=by_kind,whole=whole,delta=result['whole_delta_vs338'],warm={k:v['rows'][-1] for k,v in runs.items()},pins=len(pins)),indent=2))
if __name__=='__main__':main()
