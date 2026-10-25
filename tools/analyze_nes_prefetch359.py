# SPDX-License-Identifier: MIT
"""Separate host replacement, actual ARM hint cost and bounded cache experiment."""
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
 for mode,refmode in [('window02','window01'),('fixed01','fixed01')]:
  folder=d/mode;b=BASE/'probes/nes-raster355'/refmode;r=js(folder/'result.json');assert r['passed']
  for n,h in r['rtl_hashes'].items():assert sha(folder/n)==h;read(folder/n)
  assert load_image(folder/'output.elf')==load_image(b/'output.elf');pins[str(folder/'output.elf')]=sha(folder/'output.elf')
  assert 'PASS REFILL267 frames=3' in read(folder/'vsim.log');read(folder/'joint266_tb.sv')
  ev=list(csv.reader(read(folder/'joint-events.csv').splitlines()));bev=list(csv.reader(read(b/'joint-events.csv').splitlines()));rows=[]
  for f in (905,906,907):
   e=[x for x in ev if x[1]==str(f)];be=[x for x in bev if x[1]==str(f)];get=lambda v,n:next(x for x in v if x[0]==n)
   start=get(e,'start319');end=get(e,'frame_done');bs=get(be,'start319');bend=get(be,'frame_done');assert start[2:]==bs[2:]
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
   rows.append(dict(frame=f,total_ms=total,baseline_ms=base,delta_ms=total-base,start_ROM_cycle=int(start[3]),qualified_units=len(actual),published_chunks=published,max_credit=credit,source_SPI_bytes=sum(int(x[5]) for x in e if x[0]=='input_wire337'),wire_exact=True))
  runs[mode]=dict(rows=rows,IRQ_cases=len(r['ARM']['IRQ_cases']))
 guards=js(d/'guards01/result.json');assert guards['passed']
 for c in guards['cases']:assert f"PASS OWNER319 GUARD={c['case']}" in read(d/'guards01'/f"case{c['case']}"/'vsim.log')
 for n in ('aperture','final-raw0'):assert js(d/'guards01'/n/'result.json')['passed'];read(d/'guards01'/n/'vsim.log')
 def whole(name):
  m=js(d/name/'result.json');assert m['passed']
  for n,h in m['actual_inputs'].items():assert sha(d/name/n)==h;read(d/name/n)
  summary=read(d/name/'output_files/board.map.summary');read(d/name/'output_files/board.map.rpt')
  return {k:int(re.search(p+r'\s*:\s*([0-9,]+)',summary)[1].replace(',','')) for k,p in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Total registers'),('RAM_bits','Total memory bits')]}
 host=whole('map01');cachemap=whole('cachemap03');asyncmap=whole('cachemap01');automap=whole('cachemap02')
 for n in ('nes_mux260.sv','nes_validator278.sv','nes_joint257.sv'):
  mapped=read(d/'map01'/n)
  # Existing board wrapper exports tile_closed; simulation observes the same
  # register hierarchically. Normalize only this explicit pass-through port.
  if n=='nes_mux260.sv':
   assert mapped.count(' output wire tile_closed267,')==1
   mapped=mapped.replace(' output wire tile_closed267,','').replace('reg tiles_closed;assign tile_closed267=tiles_closed;','reg tiles_closed;')
  assert [x for x in mapped.splitlines() if x.strip()]==[x for x in read(d/'window02'/n).splitlines() if x.strip()],n
 cache=js(d/'cache01/result.json');assert cache['passed']
 for p,h in cache['pins'].items():assert sha(Path(p))==h;pins[p]=h
 assert read(d/'cache01/nes_chr_cache192.sv')==read(d/'cachemap03/nes_chr_cache192.sv')
 for phase in (5677152,7368026):read(d/'cache01'/f'phase{phase}.log')
 arm=js(d/'arm03/result.json');assert arm['passed'] and len(arm['frames'])==71 and len(arm['guards'])==4
 for n in ('decoder.elf','nes_decode280.c'):pins[str(d/'arm03'/n)]=sha(d/'arm03'/n)
 read(d/'arm03/size.log');refarm=js(BASE/'probes/nes-raw352/decoder01/result.json')
 newsize=list(map(int,arm['text_size'].splitlines()[1].split()[:3]));oldsize=list(map(int,refarm['size'].splitlines()[1].split()[:3]))
 assert (d/'arm03/prefetch907.bin').read_bytes()==(d/'arm02/prefetch907.bin').read_bytes()
 for n in ('arm02','arm03'):pins[str(d/n/'prefetch907.bin')]=sha(d/n/'prefetch907.bin')
 prefix=js(BASE/'probes/nes-exec358/prefix07/result.json')
 first=next(x for x in prefix['rows'] if x['frame']==907 and x['packet']==0)['timing']['window01']
 warm=arm['frames'][2];packet=warm['packets'][0];assert packet['length']==48 and len(packet['tags'])==17
 extra=packet['decode_extra']+packet['filter_instructions'];ready=first+extra/84000
 window_end=prefix['continuous_window_upper_ms']
 spi=48*8/2625000*1000+.008;rom=272*12/22000000*1000
 budget=dict(prefix_ms=first,window_end_upper_ms=window_end,available_ms=window_end-first,
  ARM_extra_instructions=extra,ARM_extra_CPI1_ms=extra/84000,packet_ready_ms=ready,
  packet_late_before_SPI_ms=ready-window_end,SPI_48B_plus_CS_ms=spi,ROM_272B_12clock_floor_ms=rom,
  packet_then_fill_zero_ARM_lower_bound_ms=spi+rom,zero_ARM_over_budget_ms=spi+rom-(window_end-first),
  warm_total_extra_decode_instructions=warm['decode_extra'],warm_total_filter_instructions=warm['filter_instructions'],
  ARM_text_delta=newsize[0]-oldsize[0],ARM_BSS_delta=newsize[2]-oldsize[2],ARM_observed_stack_delta=arm['stack_observed']-refarm['stack_observed'],full_firmware_bound=False,
  condition='Packet CRC complete before cache fill. Streaming SPI/ROM overlap is not ruled out by the serial lower bound; current actual ARM misses the window before any SPI regardless.')
 assert ready>window_end and budget['zero_ARM_over_budget_ms']>0
 baseline=dict(LE=22144,comb=17274,FF=9018,RAM_bits=307808)
 names=('nes_host359.py','probe_nes_host359.py','map_nes_host359.py','guard_nes_host359.py','check_nes_final359.py','nes_prefetch359.py','probe_nes_prefetch359.py','nes_cache359.py','probe_nes_cache359.py','map_nes_cache359.py','analyze_nes_prefetch359.py')
 for n in names:read(ROOT/'tools'/n)
 result=dict(stage=359,analysis_passed=True,selected_RTL=338,selected_ARM=355,candidate_selected=False,runs=runs,
  host_whole=host,host_delta_vs338={k:host[k]-baseline[k] for k in host},host_comb_deficit=host['comb']-15408,
  cache_capacity_whole=cachemap,cache_capacity_delta_vs_host={k:cachemap[k]-host[k] for k in host},async_cache_rejected_whole=asyncmap,auto_sync_cache_rejected_whole=automap,
  cache=cache,ARM_budget=budget,ARM_guards=arm['guards'],ARM_71_frames=arm['frames'],host_guards=guards['cases'],
  selected_gap_ms=20.689706-1000/60,selected_comb_deficit=1866,host_candidate_gap_ms=runs['window02']['rows'][-1]['total_ms']-1000/60,
  integrated_EA_prefetch=False,new_MAP=True,FIT=False,STA=False,physical=False,
  scope='Host tap continuation replaced by validator84MHz RAM executor; source338/ARM355 unchanged. ActualM4 prefix producer separate. Cache uses actual arbiter/READ16 with TB wire and port driver; no EA dispatcher/CDC/prefetch lease, no full joint-frame claim. Whole cache capacity MAP binds normal consumer only; excludes missing EA controls. Actual ARM355/IRQ/2slots and ordinary65816 trace plus tile/map/display model, not fullRUN/full65816/VBlank/physicalWCET.',pins=pins)
 (ROOT/'analysis/prefetch359-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
 print(json.dumps(dict(host=host,cache=cachemap,budget=budget,warm={k:v['rows'][-1] for k,v in runs.items()},pins=len(pins)),indent=2))
if __name__=='__main__':main()
