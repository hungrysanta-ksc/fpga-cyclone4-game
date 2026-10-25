# SPDX-License-Identifier: MIT
"""Same-phase and continuous whole-path evidence; inclusive areas never added twice."""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_execute334 import wire
from analyze_nes_receipt335 import load_image,completed_unit

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);d=ap.parse_args().root.resolve();pins={}
 def pin(p):p=p.resolve();pins[str(p)]=sha(p);return p
 def read(p):return pin(p).read_text(encoding='utf-8-sig')
 def js(p):return json.loads(read(p))
 runs={};baseline=BASE/'probes/nes-execute362'
 for name,refname in [('window05','keepwindow01'),('fixed01','keepfixed01')]:
  folder=d/name;ref=baseline/refname;r=js(folder/'result.json');assert r['passed']
  for n,h in r['rtl_hashes'].items():assert sha(pin(folder/n))==h
  assert load_image(pin(folder/'output.elf'))==load_image(pin(ref/'output.elf'))
  log=read(folder/'vsim.log');assert 'PASS REFILL267 frames=3' in log
  count=re.search(r'ROWS363 rows=(\d+) source=(\d+) host=(\d+)',log);assert count and all(int(x)>0 for x in count.groups())
  events=list(csv.reader(read(folder/'joint-events.csv').splitlines()));bevents=list(csv.reader(read(ref/'joint-events.csv').splitlines()));rows=[]
  hint=js(folder/'hint-arm361.json');assert hint['passed']
  for n,h in hint['pins'].items():assert sha(pin(Path(n)))==h
  assert read(folder/'hint361.hex')==read(ref/'hint361.hex')
  for f in (905,906,907):
   e=[x for x in events if x[1]==str(f)];be=[x for x in bevents if x[1]==str(f)];get=lambda v,n:next(x for x in v if x[0]==n)
   start=get(e,'start319');end=get(e,'frame_done');bs=get(be,'start319');bend=get(be,'frame_done')
   if name=='fixed01':assert start[2:]==bs[2:]
   tx=js(folder/f'arm{f}.json')['transfers'];bt=js(ref/f'arm{f}.json')['transfers'];assert wire(tx)==wire(bt)
   assert read(folder/f'frame{f}.records')==read(ref/f'frame{f}.records')
   expected=[];actual=[];offset=0;token=None;writes=[];published=0
   for x in e:
    if x[0]=='read336':
     tok,op,section,pos,off,data,t=map(int,x[2:]);assert off==offset
     if not offset:token=tok
     assert tok==token;offset+=1;u=completed_unit(op,section,pos,2)
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
   row=dict(frame=f,total_ms=total,baseline_ms=base,delta_ms=total-base,gap_ms=total-1000/60,start_ROM_cycle=int(start[3]),baseline_ROM_cycle=int(bs[3]),max_credit=credit,qualified_units=len(actual),published=published,wire_exact=True)
   row.update(source_SPI_bytes=sum(int(x[5]) for x in e if x[0]=='input_wire337'),hint_SPI_bytes=28 if f==907 else 0,output_SPI_bytes=sum(len(x['tx'])//2 for x in tx),output_progress_polls=sum(x['tx'].startswith('e2') for x in tx),output_ARM_instructions=next(x['instructions'] for x in r['ARM']['frames'] if x['frame']==f))
   row['source_empty_polls']=sum(x[0]=='input_wire337' and x[2]=='28' and x[4]=='0' for x in e)
   if f==907:
    for kind,label in [('0','BG'),('1','OBJ')]:
     for event,key in [('romplan305','plan'),('romtile305','tile')]:
      x=next(x for x in e if x[0]==event and x[2]==kind);row[label+'_'+key+'_ms']=(int(x[-1])-int(start[2]))/1e9
    row['hint_ms']={n:(int(get(e,n)[2])-int(start[2]))/1e9 for n in ('hint_start361','hint_end361','hint_fill361')}
    row['first_block_decoded_ms']=row['hint_ms']['hint_start361']-(hint['extra_instructions']+66)*r['CPI']/84000-24/84000
    row['initial_ROM_window_end_upper_ms']=(354640-int(start[3])%357368)/22000
    row['fill_margin_to_initial_window_upper_ms']=row['initial_ROM_window_end_upper_ms']-row['hint_ms']['hint_fill361']
   rows.append(row)
  runs[name]=dict(rows=rows,IRQ_cases=len(r['ARM']['IRQ_cases']),row_count=int(count[1]),source_events=int(count[2]),host_events=int(count[3]),hint=hint)
 maps={};ledger={}
 for name,folder in [('reference',baseline/'objmap01'),('candidate',d/'map02')]:
  result=js(folder/'result.json');assert result['passed']
  for n,h in result['actual_inputs'].items():assert sha(pin(folder/n))==h
  summary=read(folder/'output_files/board.map.summary');report=read(folder/'output_files/board.map.rpt')
  if name=='candidate':
   for block in ('nes_core257:encoder','nes_rows363:rows363','nes_output260:flow','nes_byte363:executor363'):
    assert any('State Machine - ' in line and block+'|state' in line for line in report.splitlines()),block
  maps[name]={k:int(re.search(p+r'\s*:\s*([0-9,]+)',summary)[1].replace(',','')) for k,p in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Total registers'),('RAM_bits','Total memory bits')]}
  ledger[name]={}
  for line in report.splitlines():
   c=[v.strip() for v in line.split(';')]
   if len(c)>5 and re.fullmatch(r'\d+ \(\d+\)',c[2]):
    key=c[1].strip('|');v=list(map(int,re.findall(r'\d+',c[2])));ledger[name][key]=dict(inclusive=v[0],self=v[1])
 nonblank=lambda s:[x for x in s.splitlines() if x.strip()]
 for n in ('nes_core257.sv','nes_transport257.sv','nes_validator278.sv','nes_joint257.sv','nes_mux260.sv'):
  mapped=read(d/'map02'/n)
  if n=='nes_mux260.sv':
   # Existing board wrapper exposes the same tiles_closed register to plan.
   assert mapped.count(' output wire tile_closed267,')==1
   assert mapped.count('assign tile_closed267=tiles_closed;')==1
   mapped=mapped.replace(' output wire tile_closed267,\n','').replace('assign tile_closed267=tiles_closed;','')
  assert nonblank(read(d/'window05'/n))==nonblank(mapped),n
  assert read(d/'window05'/n)==read(d/'fixed01'/n)
 source=read(d/'window05/nes_core257.sv');host=read(d/'window05/nes_mux260.sv');joint=read(d/'window05/nes_joint257.sv')
 assert 'FSTORE' not in source and 'SREAD' not in source and 'q_maps' not in source
 assert 'PCAP' not in host and 'PUT' not in host and 'reg [7:0] at,held' not in host
 assert 'module nes_query355' not in joint and 'nes_rows363 rows363' in joint
 assert 'always @(posedge clk)begin aq<=' in joint and 'always @(posedge host_clk)begin bq<=' in joint
 assert read(d/'window05/nes_validator278.sv')==read(baseline/'keepwindow01/nes_validator278.sv')
 guard_cases=[]
 for name in ('guards01','guards02'):
  guards=js(d/name/'result.json');assert guards['passed']
  for n,h in guards['rtl_hashes'].items():assert sha(pin(d/name/n))==h==sha(pin(d/'window05'/n))
  for c in guards['cases']:
   if name=='guards01' and c['case']==27:continue  # Startup-ready false trigger, retained only as failed test design.
   log=read(d/name/f"case{c['case']}"/'vsim.log');assert f"PASS OWNER319 GUARD={c['case']}" in log
   if c['case']==27:
    count=re.search(r'ROWS363 rows=(\d+) source=(\d+)',log);assert count and int(count[1])>0 and int(count[2])>0
    assert 'rows363.active&&dut.core.rows363.state==dut.core.rows363.SPACE&&dut.core.rows363.valid0&&dut.core.rows363.valid1' in read(d/name/'joint266_tb.sv')
   guard_cases.append(dict(c,run=name))
 assert len(guard_cases)==len({c['case'] for c in guard_cases})==10
 for n in ('aperture','final-raw0'):assert js(d/'guards01'/n/'result.json')['passed'];read(d/'guards01'/n/'vsim.log')
 # EA/cache/arbiter code is unchanged; preserve its 68-case evidence by hash.
 for n in ('nes_spi270.sv','nes_plan_spi200.sv','nes_source_tile192.sv','nes_chr_cache192.sv','nes_plan_rom267.sv','nes_rom_physical.sv','nes_native_arbiter165.sv'):
  assert read(d/'window05'/n)==read(baseline/'keepwindow01'/n)
 ea=js(baseline/'objguards02/result.json');assert ea['passed'];assert 'PASS GUARD361 cases=68' in read(baseline/'objguards02/vsim.log')
 names=['nes_joint257:core','nes_output260:flow','nes_validator278:validator','nes_bulk_aperture188:shared_ram.aperture','nes_queue260:queue','nes_spi270:spi_front270','nes_plan_batch206:transport','nes_plan_spi200:endpoint']
 l=ledger['candidate'];inc=lambda n:l[n]['inclusive']
 source_host=inc(names[0])-inc(names[2])+l[names[1]]['self']+inc('nes_byte363:executor363')
 checker=inc(names[2])+inc(names[3]);queue=inc(names[4])+inc(names[5]);plan=inc(names[6])+inc(names[7]);rest=maps['candidate']['comb']-source_host-checker-queue-plan
 cap=15253-rest-checker-650-plan
 budget=dict(source_host=source_host,independent_checker_aperture=checker,queue_SPI=queue,plan=plan,rest=rest,source_host_cap=cap,source_host_delete=source_host-cap,queue_SPI_delete=queue-650,total_delete=maps['candidate']['comb']-15253)
 for p in ROOT.glob('tools/*363.py'):pin(p)
 result=dict(stage=363,analysis_passed=True,selected_RTL=338,selected_ARM=355,candidate_selected=False,runs=runs,maps=maps,ledger=ledger,budget=budget,guards=guard_cases,EA_prior_unchanged_cases=68,whole_comb_deficit=maps['candidate']['comb']-15408,hot_byte_FSM_replaced=True,complete_source_host_orchestration_replaced=False,full_firmware_hint_loop=False,full_65816=False,FIT=False,STA=False,physical=False,pins=pins)
 (ROOT/'analysis/rows363-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
 print(json.dumps(dict(warm={k:v['rows'][-1] for k,v in runs.items()},maps=maps,budget=budget,pins=len(pins)),indent=2))
if __name__=='__main__':main()
