# SPDX-License-Identifier: MIT
"""Paired full schedules, causal M4 hints, independent publication and whole Lite."""
import argparse,csv,json,re,struct
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_execute334 import wire
from analyze_nes_receipt335 import load_image,completed_unit

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);d=ap.parse_args().root.resolve();pins={}
 def pin(p):p=p.resolve();pins[str(p)]=sha(p);return p
 def read(p):return pin(p).read_text(encoding='utf-8-sig')
 def js(p):return json.loads(read(p))
 runs={}
 for name,refname in [('window01','window02'),('fixed01','fixed01'),('objwindow01','window02'),('objfixed01','fixed01'),('keepwindow01','window02'),('keepfixed01','fixed01')]:
  hinted=name.startswith(('obj','keep'));common=not name.startswith('keep')
  folder=d/name;ref=BASE/'probes/nes-prefetch359'/refname;r=js(folder/'result.json');assert r['passed']
  for n,h in r['rtl_hashes'].items():assert sha(pin(folder/n))==h
  assert load_image(pin(folder/'output.elf'))==load_image(pin(ref/'output.elf'))
  log=read(folder/'vsim.log');assert 'PASS REFILL267 frames=3' in log
  cnt=re.search(r'CRC362 source=(\d+) checker=(\d+)',log)
  if common:assert cnt and min(map(int,cnt.groups()))>0
  read(folder/'joint266_tb.sv');ev=list(csv.reader(read(folder/'joint-events.csv').splitlines()));bev=list(csv.reader(read(ref/'joint-events.csv').splitlines()));rows=[]
  for f in (905,906,907):
   e=[x for x in ev if x[1]==str(f)];be=[x for x in bev if x[1]==str(f)];get=lambda v,n:next(x for x in v if x[0]==n)
   start=get(e,'start319');end=get(e,'frame_done');bs=get(be,'start319');bend=get(be,'frame_done')
   if 'fixed' in name:assert start[2:]==bs[2:]
   tx=js(folder/f'arm{f}.json')['transfers'];oldtx=js(ref/f'arm{f}.json')['transfers'];assert wire(tx)==wire(oldtx)
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
   row.update(source_SPI_bytes=sum(int(x[5]) for x in e if x[0]=='input_wire337'),hint_SPI_bytes=28 if hinted and f==907 else 0,output_SPI_bytes=sum(len(x['tx'])//2 for x in tx),output_progress_polls=sum(x['tx'].startswith('e2') for x in tx),output_ARM_instructions=next(x['instructions'] for x in r['ARM']['frames'] if x['frame']==f))
   row['source_empty_polls']=sum(x[0]=='input_wire337' and x[2]=='28' and x[4]=='0' for x in e)
   if f==907:
    for kind,label in [('0','BG'),('1','OBJ')]:
     for event,key in [('romplan305','plan'),('romtile305','tile')]:
      x=next(x for x in e if x[0]==event and x[2]==kind);row[label+'_'+key+'_ms']=(int(x[-1])-int(start[2]))/1e9
    if hinted:row['hint_ms']={n:(int(get(e,n)[2])-int(start[2]))/1e9 for n in ('hint_start361','hint_end361','hint_fill361')}
   rows.append(row)
  run=dict(rows=rows,IRQ_cases=len(r['ARM']['IRQ_cases']),CRC_source_events=int(cnt[1]) if common else None,CRC_checker_events=int(cnt[2]) if common else None)
  if hinted:
   hint=js(folder/'hint-arm361.json');assert hint['passed'];packet=bytes.fromhex(hint['packet']);assert len(packet)==28 and packet[1]==7
   for p,h in hint['pins'].items():assert sha(pin(Path(p)))==h
   tags=list(struct.unpack('<7H',packet[12:-2]));assert tags==[6525,6424,6426,6425,6427,5082,5080]
   # Oracle is read only after the causally bound producer result exists.
   data=pin(folder/'actual-plans293-907.bin').read_bytes();at=0;obj=set()
   while at<len(data):
    length,count=struct.unpack_from('<HB',data,at);at+=3;end=at+length
    for _ in range(count):
     op=data[at];n=(7 if op==128 else 8 if op==129 else 3) if op&128 else 16+2*data[at+1].bit_count()
     if op&3==1:obj.add(struct.unpack_from('<H',data,at+(5 if op&128 else 6))[0])
     at+=n
    assert at==end
   assert obj==set(tags[-2:]);run['hint']=hint;run['OBJ_oracle_match']=sorted(obj)
   rows[-1]['first_block_decoded_ms']=rows[-1]['hint_ms']['hint_start361']-(hint['extra_instructions']+66)*r['CPI']/84000-24/84000
   phase=rows[-1]['start_ROM_cycle']%357368
   rows[-1]['initial_ROM_window_end_upper_ms']=(354640-phase)/22000
   rows[-1]['fill_margin_to_initial_window_upper_ms']=rows[-1]['initial_ROM_window_end_upper_ms']-rows[-1]['hint_ms']['hint_fill361']
  runs[name]=run
 maps={};ledgers={}
 names=['nes_joint257:core','nes_output260:flow','nes_validator278:validator','nes_bulk_aperture188:shared_ram.aperture','nes_queue260:queue','nes_spi270:spi_front270','nes_plan_batch206:transport','nes_plan_spi200:endpoint']
 for name in ('map01','map02','objmap01','jointmap01'):
  m=js(d/name/'result.json');assert m['passed']
  for n,h in m['actual_inputs'].items():assert sha(pin(d/name/n))==h
  summary=read(d/name/'output_files/board.map.summary');report=read(d/name/'output_files/board.map.rpt')
  maps[name]={k:int(re.search(p+r'\s*:\s*([0-9,]+)',summary)[1].replace(',','')) for k,p in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Total registers'),('RAM_bits','Total memory bits')]}
  ledger={}
  for line in report.splitlines():
   c=[v.strip() for v in line.split(';')]
   if len(c)>5 and c[1].strip('|') in names:
    v=list(map(int,re.findall(r'\d+',c[2])));ledger[c[1].strip('|')]=dict(inclusive=v[0],self=v[1])
  ledgers[name]=ledger
 for folder,mapped in [('window01','map01'),('objwindow01','jointmap01')]:
  for n in ('nes_core257.sv','nes_transport257.sv','nes_validator278.sv','nes_joint257.sv'):
   # Legacy board transport generator leaves one additional blank line.
   nonblank=lambda s:[x for x in s.splitlines() if x.strip()]
   assert nonblank(read(d/folder/n))==nonblank(read(d/mapped/n)),(folder,n)
  source=read(d/folder/'nes_core257.sv');transport=read(d/folder/'nes_transport257.sv')
  assert 'function automatic [15:0] crc16(' not in source
  assert 'nes_native_mailbox206' not in transport and 'reg [23:0] descriptor0,descriptor1;' in transport
 for n in ('nes_spi270.sv','nes_plan_spi200.sv','nes_source_tile192.sv'):
  assert read(d/'objwindow01'/n)==read(d/'jointmap01'/n)
 normalize=lambda s:s.replace('wire pending=state==WAIT;wire hit=state==HIT;wire hit_reply=state==REPLY;','wire pending=state==WAIT;')
 assert normalize(read(d/'objwindow01/nes_chr_cache192.sv'))==read(d/'jointmap01/nes_chr_cache192.sv')
 for n in ('nes_core257.sv','nes_transport257.sv','nes_mux260.sv','nes_validator278.sv','nes_joint257.sv'):
  assert read(d/'keepwindow01'/n)==read(BASE/'probes/nes-prefetch359/window02'/n),n
 for n in ('nes_spi270.sv','nes_plan_spi200.sv','nes_source_tile192.sv'):
  assert read(d/'keepwindow01'/n)==read(d/'objmap01'/n)
 assert normalize(read(d/'keepwindow01/nes_chr_cache192.sv'))==read(d/'objmap01/nes_chr_cache192.sv')
 guards=js(d/'guards01/result.json');assert guards['passed']
 for n,h in guards['rtl_hashes'].items():assert sha(pin(d/'guards01'/n))==h==sha(pin(d/'window01'/n))
 for c in guards['cases']:assert f"PASS OWNER319 GUARD={c['case']}" in read(d/'guards01'/f"case{c['case']}"/'vsim.log')
 for n in ('aperture','final-raw0'):assert js(d/'guards01'/n/'result.json')['passed'];read(d/'guards01'/n/'vsim.log')
 objguards=js(d/'objguards02/result.json');assert objguards['passed']
 for p,h in objguards['pins'].items():assert sha(pin(Path(p)))==h
 assert 'PASS GUARD361 cases=68' in read(d/'objguards02/vsim.log')
 assert 'Errors: 0, Warnings: 0' in read(d/'objguards02/vsim.log')
 arm=js(d/'arm03/result.json');assert arm['passed']
 for p,h in arm['pins'].items():assert sha(pin(Path(p)))==h
 ledger=ledgers['jointmap01'];inc=lambda n:ledger[n]['inclusive']
 source=inc(names[0])-inc(names[2])+ledger[names[1]]['self'];checker=inc(names[2])+inc(names[3]);queue=inc(names[4])+inc(names[5]);plan=inc(names[6])+inc(names[7]);rest=maps['jointmap01']['comb']-source-checker-queue-plan
 cap=15253-rest-checker-650-plan
 budget=dict(source_host_including_query_CDC_shared_CRC=source,independent_checker_aperture=checker,queue_SPI=queue,plan=plan,rest=rest,source_host_cap=cap,source_host_delete=source-cap,queue_SPI_delete=queue-650,total_delete=maps['jointmap01']['comb']-15253)
 ledger=ledgers['objmap01'];source=inc(names[0])-inc(names[2])+ledger[names[1]]['self'];checker=inc(names[2])+inc(names[3]);queue=inc(names[4])+inc(names[5]);plan=inc(names[6])+inc(names[7]);rest=maps['objmap01']['comb']-source-checker-queue-plan;cap=15253-rest-checker-650-plan
 keep_budget=dict(source_host=source,independent_checker_aperture=checker,queue_SPI=queue,plan=plan,rest=rest,source_host_cap=cap,source_host_delete=source-cap,queue_SPI_delete=queue-650,total_delete=maps['objmap01']['comb']-15253)
 for p in ROOT.glob('tools/*362.py'):pin(p)
 result=dict(stage=362,analysis_passed=True,selected_RTL=338,selected_ARM=355,host359_preserved=True,candidate_selected=False,runs=runs,maps=maps,ledgers=ledgers,budget=budget,keep_source_budget=keep_budget,guards=guards['cases'],EA_guard_cases=68,ARM_probe=arm,selected_gap_ms=20.689706-1000/60,selected_comb_deficit=1866,joint_comb_deficit=maps['jointmap01']['comb']-15408,keep_source_comb_deficit=maps['objmap01']['comb']-15408,wide_source_host_FSM_replacement=False,shared_CRC_and_transport_CDC_replacement=True,full_firmware_hint_loop=False,FIT=False,STA=False,physical=False,scope=__doc__,pins=pins)
 (ROOT/'analysis/execute362-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
 print(json.dumps(dict(warm={k:v['rows'][-1] for k,v in runs.items()},maps=maps,budget=budget,pins=len(pins)),indent=2))
if __name__=='__main__':main()
