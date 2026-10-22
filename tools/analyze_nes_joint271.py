# SPDX-License-Identifier: MIT
"""Compare measured271 polling candidates and pin the next RAM/CDC boundary."""
from pathlib import Path
import argparse,collections,csv,json,re
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_boundary269 import hierarchy

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--spi',default='spiguards01');a=p.parse_args();b=a.base.resolve();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
 pins={}
 def pin(p):pins[str(p)]=sha(p);return p
 def read(p):return json.loads(pin(p).read_text(encoding='utf-8'))
 old269=read(ROOT/'analysis/joint269-verification.json');old270=read(ROOT/'analysis/joint270-verification.json')
 refs={269:{'normal':BASE/'probes/nes-joint269/joint02','restricted':BASE/'probes/nes-joint269/window01'},270:{'normal':BASE/'probes/nes-joint270/test05','restricted':BASE/'probes/nes-joint270/window01'}}
 def metrics(q):
  ev=list(csv.reader(pin(q/'joint-events.csv').open()));source={int(x['frame']):x for x in csv.DictReader(pin(q/'cycles.csv').open())}
  r=read(q/'result.json');assert r['passed'];arm={x['frame']:x for x in r['ARM']['frames']};rows={}
  for x in ev:
   if x[0]!='frame_done':continue
   f=int(x[1]);c=collections.Counter();wire=collections.Counter()
   for e in ev:
    if e[0]=='arm267' and int(e[1])==f:c[int(e[2])]+=1;wire[int(e[2])]+=int(e[3])
   sm=int(source[f]['total'])*45.454/1e6;out=int(x[3])/1e9
   rows[f]=dict(source_ms=sm,output_ms=out,serial_ms=sm+out,gap_ms=sm+out-1000/60,
    E0=c[224],E2=c[226],E1=c[225],status_polls=c[224]+c[226],SPI_bytes=arm[f]['SPI_bytes'],instructions=arm[f]['instructions'])
  return r,rows
 prior={k:{mode:metrics(q)[1] for mode,q in modes.items()} for k,modes in refs.items()}
 results={};rows=[];packets={};pause_previous={}
 for variant,modes in {'A':{'normal':'test01','restricted':'window01'},'B':{'normal':'test02','restricted':'window02'}}.items():
  for mode,name in modes.items():
   q=b/name;r,m=metrics(q);assert r['frames']==3 and set(m)=={905,906,907};results[name]=r
   pause_previous[name]=(0,0)
   for f,x in m.items():
    tr=read(q/f'arm{f}.json')['transfers'];tx=[t['tx'] for t in tr if t['tx'].startswith('e1')]
    reftr=read(refs[270][mode]/f'arm{f}.json')['transfers']
    assert tx==[t['tx'] for t in reftr if t['tx'].startswith('e1')],(name,f)
    packets[f]=len(tx);pc,pi=pause_previous[name];last=tr[-1]
    calls=last['pause_calls']-pc;iterations=last['pause_iterations']-pi;pause_previous[name]=(last['pause_calls'],last['pause_iterations'])
    rows.append(dict(variant=variant,mode=mode,frame=f,**x,delta269_ms=x['serial_ms']-prior[269][mode][f]['serial_ms'],
     delta270_ms=x['serial_ms']-prior[270][mode][f]['serial_ms'],pause_calls=calls,pause_iterations=iterations,
     pause_CPI1_reference_ms=(iterations*5+calls*5)/84000))
   assert r['tb_sha256']==sha(pin(q/'joint266_tb.sv'))
   assert r['ELF_sha256']==sha(pin(q/'output.elf'))
   for n in ['CPU-bus.csv','CPU-ordinary.sfc','CPU-packets.hex','nes_core257.sv','nes_plan_batch206.sv']:
    assert pin(q/n).read_bytes()==pin(refs[270][mode]/n).read_bytes()
   for f in [905,906,907]:assert pin(q/f'all{f}.hex').read_bytes()==pin(refs[270][mode]/f'all{f}.hex').read_bytes()
   reference=read(refs[270][mode]/'result.json')['rtl_hashes']
   assert set(r['rtl_hashes'])==set(reference)
   changed=[n for n,h in r['rtl_hashes'].items() if h!=reference[n]]
   assert changed==([] if variant=='A' else ['nes_spi270.sv']),changed
 for variant,left,right,guard in [('A','test01','window01','armguards01'),('B','test02','window02','armguards03')]:
  assert pin(b/left/'nes_output264.c').read_bytes()==pin(b/right/'nes_output264.c').read_bytes()
  g=read(b/guard/'result.json');assert g['ELF_sha256']==results[right]['ELF_sha256'] and len(g['backoff_guards'])==4
  if variant=='B':assert len(g['E1_snapshot_guards'])==6
 assert pin(b/'test02/nes_output264.c').read_bytes()==pin(ROOT/'tools/nes_output271.c').read_bytes()
 assert pin(b/'test01/nes_output264.c').read_bytes()==pin(ROOT/'tools/nes_output271_phase.c').read_bytes()
 spi=read(b/a.spi/'result.json');assert spi['passed']
 board=read(b/'board01/result.json');assert board['passed']
 for q in [b/'window02',b/'test02',b/'board01',b/a.spi]:
  assert pin(q/'nes_spi270.sv').read_bytes()==pin(ROOT/'tools/nes_spi271.sv').read_bytes()
 area={k:int(re.search(pat+r'\s*:\s*([\d,]+)',board['summary']).group(1).replace(',','')) for k,pat in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
 h=hierarchy(pin(b/'board01/output_files/board.map.rpt'))
 region={n:h[n]['comb'] for n in old270['replacement']['current_region'] if n!='output exclusive'}
 region['output exclusive']=h['|nes_output257:flow|']['own_comb'] if '|nes_output257:flow|' in h else h['|nes_output260:flow|']['own_comb']
 layout=[('validity',0,331),('retained CRC',332,395),('receipts',396,561),('map coverage',562,817),('H2',832,863),('display offset',864,867)]
 used=set()
 for _,lo,hi in layout:
  span=set(range(lo,hi+1));assert not used&span;used|=span
 free=set(range(1024))-used;assert len(free)==170 and not set(range(868,1024))&used
 core=pin(BASE/'probes/nes-joint270/board02/nes_core257.sv').read_text()
 queue=pin(BASE/'probes/nes-joint270/board02/nes_queue260.sv').read_text()
 flow=pin(BASE/'probes/nes-joint270/board02/nes_mux260.sv').read_text()
 assert "10'd864" in core and "10'd832" in core and 'cursor==817' in core
 assert 'always @(posedge clk)read_data<=buffer' in queue and 'state==NORMAL?asyn[7:0]:parser_address' in flow
 assert '.src_clk(host_clk),.dst_clk(nes_clk)' in flow and '#(.WIDTH(24)) consumed' in flow
 with (d/'costs.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 warm=[x for x in rows if x['frame']==907];restricted=[x for x in warm if x['mode']=='restricted']
 result=dict(passed=True,stage='NES271',selected=['test01','window01','armguards01','test02','window02','armguards03',a.spi,'board01'],
  measured_frames_per_candidate_per_mode=3,new_full71=False,prior71='analysis/joint270-verification.json',warm907=warm,
  MAP=dict(A_reused270=old270['MAP']['current270'],B=area,deltaB270={k:area[k]-old270['MAP']['current270'][k] for k in area},comb_deficit=area['comb']-15408,FIT=False,STA=False),
  ARM_sizes={n:pin(b/n/'size-rom.log').read_text() for n in ['test01','test02']},
  ARM_stack={n:results[n]['ARM']['stack_observed'] for n in results},
  SPI_guard=spi,ARM_guard_B=read(b/'armguards03/result.json'),
  boundary=dict(layout=layout,output_phase_free_bytes=len(free),free_ranges=[[818,831],[868,1023]],full256B_shortfall=256-len(free),
   header28B_candidate=[868,895],contiguous128B_candidate=[896,1023],candidate_buffer_implemented=False,
   current_B_region=region,current_B_region_comb=sum(region.values()),B_new_region_limit=sum(region.values())-(area['comb']-15408),
   future_reference='270 common SPI; rejected E1 extra logic is not carried into the baseline budget',
   base270_region=old270['replacement'],new_parser_core_area=None,
   alternatives=[
    dict(name='NES queue read port',extra_RAM_bits=None,new_CDC=None,SNES_read_timing_verified=False,decision='No free clock mux: preserve SNES host read or charge a new bridge/replica.'),
    dict(name='host RAM reader to existing24bit mailbox',extra_RAM_bits=0,extra_RAM_bits_status='design constraint, NOT synthesized proof',new_CDC=None,decision='Candidate boundary: stream bounded bytes; retain SNES port, head lifetime, DMA receipt and final ACK. Parser/control area and service are unproven.'),
    dict(name='copy full256B packet into phase RAM',extra_RAM_bits=None,decision='Does not fit fixed live layout:170B free,86B short. No valid map/CRC/H2 bytes may be overwritten.')]),
  decision='Reject standalone adoption of both polling candidates; restricted warm907 remains slower than269 and no whole-area recovery.' if all(x['delta269_ms']>0 for x in restricted) else 'Timing result is conditional; whole-board area still fails. No adoption.',
  full_path_ms=None,P2_selected=False,physical60fps=False,
  limitations=['Only905..907 newly executed in each normal/restricted scenario; no new heavy-frame or71-frame claim.',
   'Busy-loop instruction count charged at CPI1; not hardware timing, WFI, full RUN or NVIC preemption.',
   'Actual26965816 ordinary bus traces; map/tile/final display still modeled. Synthetic ROM competitors.',
   'E1 snapshot precedes current admission; bad response can follow a physically accepted packet. Sticky stop and coherent reset are required, not retry.',
   'Next source/receipt/parser replacement is a boundary proposal, not RTL or area savings.'],pins=pins,script_sha256=sha(Path(__file__)))
 (d/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({k:result[k] for k in ['warm907','MAP','decision']},ensure_ascii=False))

if __name__=='__main__':main()
