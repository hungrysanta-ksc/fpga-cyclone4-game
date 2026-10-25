# SPDX-License-Identifier: MIT
"""Whole EA integration ledger: causal timing, independent read evidence, Lite."""
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
 old=js(ROOT/'analysis/prefetch359-verification.json');assert old['analysis_passed']
 runs={}
 for name,refname in [('window04','window02'),('fixed01','fixed01')]:
  folder=d/name;ref=BASE/'probes/nes-prefetch359'/refname;r=js(folder/'result.json');assert r['passed']
  for n,h in r['rtl_hashes'].items():assert sha(pin(folder/n))==h
  assert load_image(pin(folder/'output.elf'))==load_image(pin(ref/'output.elf'))
  for n in ('nes_core257.sv','nes_transport257.sv','nes_mux260.sv','nes_validator278.sv'):
   assert read(folder/n)==read(ref/n),('remaining control is no longer baseline',n)
  hint=js(folder/'hint-arm361.json');assert hint['passed'] and hint['extra_instructions']==3631
  for p,h in hint['pins'].items():assert sha(pin(Path(p)))==h
  read(folder/'joint266_tb.sv');read(folder/'vsim.log');read(folder/'hint361.hex')
  ev=list(csv.reader(read(folder/'joint-events.csv').splitlines()));bev=list(csv.reader(read(ref/'joint-events.csv').splitlines()));rows=[]
  for f in (905,906,907):
   e=[x for x in ev if x[1]==str(f)];be=[x for x in bev if x[1]==str(f)];get=lambda v,n:next(x for x in v if x[0]==n)
   start=get(e,'start319');end=get(e,'frame_done');bs=get(be,'start319');bend=get(be,'frame_done')
   if name=='fixed01':assert start[2:]==bs[2:]
   tx=js(folder/f'arm{f}.json')['transfers'];oldtx=js(ref/f'arm{f}.json')['transfers'];assert wire(tx)==wire(oldtx)
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
   row=dict(frame=f,total_ms=total,baseline_ms=base,delta_ms=total-base,gap_ms=total-1000/60,start_ROM_cycle=int(start[3]),baseline_ROM_cycle=int(bs[3]),credit=credit,qualified_units=len(actual),published=published,wire_exact=True)
   row.update(source_SPI_bytes=sum(int(x[5]) for x in e if x[0]=='input_wire337'),hint_SPI_bytes=24 if f==907 else 0,output_SPI_bytes=sum(len(x['tx'])//2 for x in tx),baseline_output_SPI_bytes=sum(len(x['tx'])//2 for x in oldtx),output_progress_polls=sum(x['tx'].startswith('e2') for x in tx),output_ARM_instructions=next(x['instructions'] for x in r['ARM']['frames'] if x['frame']==f))
   if f==907:
    row['hint_ms']={n:(int(get(e,n)[2])-int(start[2]))/1e9 for n in ('hint_start361','hint_end361','hint_fill361')}
    obj=[x for x in e if x[0]=='romplan305' and x[2]=='1'];tiles=[x for x in e if x[0]=='romtile305' and x[2]=='1']
    row['OBJ_first_plan_ms']=(int(obj[0][-1])-int(start[2]))/1e9;row['OBJ_first_tile_ms']=(int(tiles[0][-1])-int(start[2]))/1e9
   rows.append(row)
  runs[name]=dict(rows=rows,IRQ_cases=len(r['ARM']['IRQ_cases']),actual_hint=hint)
 guards=js(d/'guards05/result.json');assert guards['passed'];read(d/'guards05/vsim.log')
 for p,h in guards['pins'].items():assert sha(pin(Path(p)))==h
 assert 'PASS GUARD361 cases=60' in read(d/'guards05/vsim.log')
 m=js(d/'map02/result.json');assert m['passed']
 for n,h in m['actual_inputs'].items():assert sha(pin(d/'map02'/n))==h
 s=read(d/'map02/output_files/board.map.summary');report=read(d/'map02/output_files/board.map.rpt')
 whole={k:int(re.search(p+r'\s*:\s*([0-9,]+)',s)[1].replace(',','')) for k,p in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Total registers'),('RAM_bits','Total memory bits')]}
 assert whole==dict(LE=22499,comb=17576,FF=9093,RAM_bits=308832)
 for n in ('nes_spi270.sv','nes_plan_spi200.sv','nes_source_tile192.sv'):
  assert read(d/'map02'/n)==read(d/'window04'/n)==read(d/'fixed01'/n)
 cache_normal=lambda s:s.replace('wire pending=state==WAIT;wire hit=state==HIT;wire hit_reply=state==REPLY;','wire pending=state==WAIT;')
 assert read(d/'map02/nes_chr_cache192.sv')==cache_normal(read(d/'window04/nes_chr_cache192.sv'))==cache_normal(read(d/'fixed01/nes_chr_cache192.sv'))
 module=lambda t:t[t.index('module nes_hint361'):]
 assert module(read(d/'map02/nes_plan_path267.sv'))==module(read(d/'window04/nes_plan_rom267.sv'))
 ledger={}
 names=['nes_core257:encoder','nes_transport257:transport','nes_output260:flow','nes_validator278:validator','nes_bulk_aperture188:shared_ram.aperture','nes_queue260:queue','nes_spi270:spi_front270','nes_plan_batch206:transport','nes_plan_spi200:endpoint','nes_hint361:hint']
 for line in report.splitlines():
  c=[v.strip() for v in line.split(';')]
  if len(c)>5 and c[1].strip('|') in names:
   name=c[1].strip('|');v=list(map(int,re.findall(r'\d+',c[2])));ledger[name]=dict(inclusive=v[0],self=v[1])
 source=sum(ledger[n]['self' if n=='nes_output260:flow' else 'inclusive'] for n in names[:3]);checker=sum(ledger[n]['inclusive'] for n in names[3:5]);queue=sum(ledger[n]['inclusive'] for n in names[5:7]);plan=sum(ledger[n]['inclusive'] for n in names[7:9]);rest=whole['comb']-source-checker-queue-plan
 cap=15253-rest-checker-650-plan
 budget=dict(source_host=source,checker=checker,queue_SPI=queue,plan=plan,rest_including_hint_cache=rest,source_host_cap=cap,source_host_delete=source-cap,queue_SPI_delete=queue-650,total_delete=whole['comb']-15253)
 for p in ROOT.glob('tools/*361.py'):pin(p)
 result=dict(stage=361,analysis_passed=True,selected_RTL=338,selected_ARM=355,candidate_selected=False,runs=runs,whole=whole,whole_delta_vs359={k:whole[k]-old['host_whole'][k] for k in whole},comb_deficit=whole['comb']-15408,ledger=ledger,budget=budget,guards=guards,selected_gap_ms=old['selected_gap_ms'],selected_comb_deficit=1866,
  actual_EA_receiver=True,actual_shared_SPI=True,actual_M4_hint_at_received_block=True,full_firmware_hint_loop=False,wide_source_host_replacement=False,FIT=False,STA=False,physical=False,
  scope='Source input instruction replay now invokes M4 hint producer on received block and previous actual ARM commit RAM. TB schedules its instructions plus measured IRQ body/allocated exception and pin SPI; no full firmware ingress/ISR preemption proof. Output ARM/IRQ/2slots, ROM and independent read verification integrated. Existing ordinary65816 trace and tile/display model, not full VBlank CPU or physical WCET. Wide source-host control replacement is not implemented; added hint costs fail whole area gate.',pins=pins)
 (ROOT/'analysis/hint361-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(dict(runs={k:v['rows'] for k,v in runs.items()},whole=whole,budget=budget,pins=len(pins)),indent=2))
if __name__=='__main__':main()
