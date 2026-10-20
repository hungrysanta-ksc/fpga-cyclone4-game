# SPDX-License-Identifier: MIT
"""Measure actual split scheduling separately from future inline programs."""
from pathlib import Path
import argparse,collections,csv,json,re
from nes_delta231 import BASE,ROOT,sha
from probe_nes_joint264 import packets
from probe_nes_primitive273 import Producer,events as decode,oracle
from probe_nes_arm264 import u16
from probe_nes_split274 import canonical
from nes_split274 import source as generated_source

def program_cost(b,d):
 elf=BASE/'probes/nes-joint273/arm05/output.elf'
 producer=Producer(elf);rows=[];pins={str(elf):sha(elf)}
 for f in range(905,976):
  path=b/f'arm01/frame{f}.packets';pp=packets(path);pins[str(path)]=sha(path)
  producer.call('reset273',[f-904,u16(pp[0],8)])
  for p in pp:
   ok,program,count=producer.packet(p,2)
   assert ok==len(program)+1 and decode(program,2,p)==oracle(p,u16(pp[0],30),pp[0][36])
   assert len(p)+(len(program)+2 if program else 0)<=256
   rows.append(dict(frame=f,sequence=u16(p,2),program=program.hex(),instructions=count))
  assert producer.call('complete273',[])==1
 r=dict(passed=True,scope='Standalone273 refs16 producer on new split packets; no SPI or FPGA execution.',
        rows=rows,pins=pins,script_sha256=sha(Path(__file__)))
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
 print('Measured refs16 producer:',len(rows),'packets',sum(x['instructions'] for x in rows),'instructions')

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--base',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--program-only',action='store_true')
 a=ap.parse_args();b=a.base.resolve();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
 if a.program_only:return program_cost(b,d)
 pins={}
 def pin(p):pins[str(p)]=sha(p);return p
 def read(p):return json.loads(pin(p).read_text(encoding='utf-8'))
 def csvrows(p):return list(csv.DictReader(pin(p).open()))
 def events(q):return list(csv.reader(pin(q/'joint-events.csv').open()))
 def done(ev):return {int(x[1]):int(x[3])/1e9 for x in ev if x[0]=='frame_done'}
 selected=['arm01','armguards01','cpu01','test01','window01','guards01','program01']
 result={n:read(b/n/'result.json') for n in selected}
 assert all(r['passed'] for r in result.values())
 assert result['arm01']['packet_count']==1231 and result['arm01']['max_slot']==256
 assert result['arm01']['ordinary_count']==544 and len(result['armguards01']['split_guards'])==16
 assert result['armguards01']['partial_RLE_preflight']['passed']
 assert result['guards01']['guards']==[3,23,29,39,40,41,42,43,44]
 fault_codes={}
 for i in result['guards01']['guards']:
  log=pin(b/f'guards01/guard{i}.log').read_text()
  fault_codes[i]=int(re.search(rf'PASS SPLIT274 GNEG={i} fault=(\d+)',log).group(1))
 assert fault_codes[44]==3  # Core manifest/receipt coverage rejection.
 prior=BASE/'probes/nes-joint270';q=b/'test01'
 base=read(ROOT/'analysis/joint270-verification.json')
 assert base['MAP']['current270']['comb']==17680 and base['MAP']['comb_deficit']==2272
 old={int(x['frame']):x for x in csvrows(ROOT/'analysis/joint270-costs.csv')}
 original=read(prior/'test05/result.json')
 assert result['test01']['rtl_hashes']==original['rtl_hashes']
 for name in ['blocks.txt','commands.hex','stream.hex','expected.hex','hashes.hex','certs.hex']:
  assert pin(q/name).read_bytes()==pin(prior/'test05'/name).read_bytes(),name
 source_bytes=sum(int(line.split()[2]) for line in (q/'blocks.txt').read_text().splitlines())
 assert source_bytes==83240
 for n,h in original['rtl_hashes'].items():
  assert sha(pin(q/n))==sha(pin(prior/'test05'/n))==h
  assert sha(pin(b/'window01'/n))==h
 for n,h in result['guards01']['rtl_hashes'].items():
  assert sha(pin(b/'guards01'/n))==sha(pin(prior/'guards01'/n))==h
 for folder in ['test01','window01','arm01']:
  assert pin(b/folder/'nes_output264.c').read_text()==generated_source()
 assert sha(pin(q/'joint266_tb.sv'))==result['test01']['tb_sha256']
 assert sha(pin(q/'output.elf'))==result['test01']['ELF_sha256']
 assert sha(pin(b/'arm01/output.elf'))==result['armguards01']['ELF_sha256']
 assert pin(b/'cpu01/ordinary.sfc').read_bytes()==pin(BASE/'probes/nes-joint269/cpu01/ordinary.sfc').read_bytes()
 assert pin(q/'CPU-bus.csv').read_bytes()==pin(b/'cpu01/bus.csv').read_bytes()
 assert pin(q/'CPU-packets.hex').read_bytes()==pin(b/'cpu01/packets.hex').read_bytes()
 ev=events(q);times=done(ev);arm={r['frame']:r for r in result['test01']['ARM']['frames']}
 oldev=events(prior/'test05')
 event_instructions=collections.Counter();old_event_instructions=collections.Counter()
 for ee,counts in [(ev,event_instructions),(oldev,old_event_instructions)]:
  for x in ee:
   if x[0]=='arm267':counts[int(x[1])]+=int(x[5])
 assert len(times)==len(arm)==71 and sum(x[0]=='cpu267' for x in ev)==544
 assert sum(x[0]=='receipt' for x in ev)==2069
 assert max(int(x[2]) for x in ev if x[0]=='credits')==4
 sr={int(x['frame']):x for x in csvrows(q/'cycles.csv')}
 cpu=csvrows(b/'cpu01/timing.csv');oldcpu=csvrows(BASE/'probes/nes-joint269/cpu01/timing.csv')
 def cpu_frame(rr,f):
  cc=[x for x in rr if int(x['serial'])==f-904]
  return dict(commands=len(cc),**{k:sum(int(x[k]) for x in cc) for k in
       ('total_clocks','dma_setup_service_clocks','dma_bytes','output_bytes')})
 elf=pin(BASE/'probes/nes-joint273/arm05/output.elf')
 assert sha(elf)==result['arm01']['primitive_ELF_sha256']
 for path,h in result['program01']['pins'].items():assert sha(pin(Path(path)))==h
 assert sha(pin(b/'program01/analyze_nes_joint274.py'))==result['program01']['script_sha256']
 measured={(x['frame'],x['sequence']):x for x in result['program01']['rows']}
 assert len(measured)==1231
 rows=[];prior_wire=prior_output=0;slots=[];program_rows=[];op_counts=collections.Counter()
 for f in range(905,976):
  pp=packets(pin(b/f'arm01/frame{f}.packets'))
  op_counts.update(p[0] for p in pp)
  transfers=read(q/f'arm{f}.json')['transfers']
  assert pp==[bytes.fromhex(x['tx'])[1:-2] for x in transfers if x['tx'].startswith('e1')]
  prevpp=[bytes.fromhex(x['tx'])[1:-2] for x in read(prior/f'test05/arm{f}.json')['transfers'] if x['tx'].startswith('e1')]
  assert canonical(pp)==canonical(prevpp)
  stored=read(b/f'arm01/frame{f}.programs.json');assert len(stored)==len(pp)
  added=ins=program_bytes=0
  for p,record in zip(pp,stored):
   m=measured[(f,u16(p,2))];program=bytes.fromhex(m['program']);count=m['instructions'];ins+=count
   assert program.hex()==record['program']
   assert decode(program,2,p)==oracle(p,u16(pp[0],30),pp[0][36])
   slot=len(p)+(2+len(program) if program else 0);assert slot<=256
   assert slot==record['required_slot_bytes'];slots.append(slot)
   if program:added+=2+len(program);program_bytes+=len(program)
   program_rows.append(dict(frame=f,sequence=u16(p,2),bytes=len(program),instructions=count,slot=slot))
  count=collections.Counter();wire=collections.Counter()
  for x in ev:
   if x[0]=='arm267' and int(x[1])==f:
    count[int(x[2])]+=1;wire[int(x[2])]+=int(x[3])
  assert sum(wire.values())==arm[f]['SPI_bytes']
  cumulative=int(sr[f]['wirebytes_cumulative'])
  source_wire=cumulative-prior_wire-prior_output;prior_wire=cumulative;prior_output=arm[f]['SPI_bytes']
  assert source_wire==int(old[f]['source_SPI_bytes'])
  sm=int(sr[f]['total'])*45.454/1e6;total=sm+times[f];c=cpu_frame(cpu,f);oc=cpu_frame(oldcpu,f)
  assert c['dma_bytes']==oc['dma_bytes'] and c['output_bytes']==oc['output_bytes']
  e1=sum(len(p)+3 for p in pp);old_e1=sum(len(p)+3 for p in prevpp);assert wire[225]==e1
  rows.append(dict(frame=f,packets=len(pp),prior_packets=len(prevpp),E1_wire=e1,E1_wire_delta=e1-old_e1,
   source_ms=sm,output_schedule_ms=times[f],diagnostic_serial_ms=total,
   prior270_ms=float(old[f]['diagnostic_serial_ms']),delta_ms=total-float(old[f]['diagnostic_serial_ms']),
   budget_gap_ms=total-1000/60,ARM_instructions=arm[f]['instructions'],
   ARM_instruction_delta=arm[f]['instructions']-int(old[f]['ARM_instructions']),
   ARM_IRQ_event_instructions=event_instructions[f],
   ARM_IRQ_event_instruction_delta=event_instructions[f]-old_event_instructions[f],
   SPI_bytes=arm[f]['SPI_bytes'],source_SPI_bytes=source_wire,shared_SPI_bytes=source_wire+arm[f]['SPI_bytes'],
   E0_full=count[224],E2_short=count[226],status_polls=count[224]+count[226],
   E8_polls=count[232],E9_batches=count[233],EA_retire=count[234],
   CPU_commands=c['commands'],CPU_delta_commands=c['commands']-oc['commands'],
   CPU_master_clocks=c['total_clocks'],CPU_delta_clocks=c['total_clocks']-oc['total_clocks'],
   CPU_DMA_bytes=c['dma_bytes'],CPU_output_bytes=c['output_bytes'],
   future_program_bytes=program_bytes,future_inline_extra_wire=added,future_producer_instructions=ins,
   future_additive_sensitivity_ms=ins/84000+added*8/2625,
   future_unchanged_poll_serial_sensitivity_ms=total+ins/84000+added*8/2625))
 for name,rr in [('costs.csv',rows),('programs.csv',program_rows)]:
  with (d/name).open('w',newline='') as h:
   w=csv.DictWriter(h,fieldnames=list(rr[0]),lineterminator='\n');w.writeheader();w.writerows(rr)
 window=[];we=events(b/'window01');pe=events(prior/'window01')
 ws={int(x['frame']):x for x in csvrows(b/'window01/cycles.csv')}
 assert result['window01']['ROM_window']==1 and result['window01']['frames']==3
 for f,t in done(we).items():
  sm=int(ws[f]['total'])*45.454/1e6
  before=next(x for x in base['restricted_ROM'] if x['frame']==f)
  counts=[];wires=[];instructions=[]
  for ee in (we,pe):
   cc=collections.Counter();ww=collections.Counter();ii=0
   for x in ee:
    if x[0]=='arm267' and int(x[1])==f:
     cc[int(x[2])]+=1;ww[int(x[2])]+=int(x[3]);ii+=int(x[5])
   counts.append(cc);wires.append(ww);instructions.append(ii)
  window.append(dict(frame=f,source_ms=sm,output_schedule_ms=t,diagnostic_serial_ms=sm+t,
   prior270_ms=before['diagnostic_serial_ms'],delta_ms=sm+t-before['diagnostic_serial_ms'],
   budget_gap_ms=sm+t-1000/60,
   status_polls=counts[0][224]+counts[0][226],E2_short=counts[0][226],prior_E2_short=counts[1][226],
   SPI_delta=sum(wires[0].values())-sum(wires[1].values()),
   ARM_IRQ_event_instruction_delta=instructions[0]-instructions[1]))
 absolute_end=lambda ee:int(next(x for x in ee if x[0]=='frame_done' and x[1]=='907')[2])/1e9
 sequence=dict(first_two_delta_ms=sum(x['delta_ms'] for x in window[:2]),
  three_frame_diagnostic_delta_ms=sum(x['delta_ms'] for x in window),
  final_absolute_completion_delta_ms=absolute_end(we)-absolute_end(pe),
  interpretation='Later cold work shifts the restricted-window wait into preceding frames. Warm907 improvement is not a2ms reduction of the whole three-frame execution.')
 warm=rows[2:];worst=max(warm,key=lambda x:x['diagnostic_serial_ms'])
 assert op_counts[14]==124
 final=dict(passed=True,stage='NES274',selected=selected+['analysis01'],script_sha256=sha(Path(__file__)),
  scope=__doc__,frames=71,source_bytes=source_bytes,map_batches=op_counts[14],map_ranges=2069,max_credit=4,
  packets=1231,prior_packets=1181,inline_overflow_before=50,inline_overflow_after=0,max_slot=max(slots),
  SPI=dict(output_bytes=sum(x['SPI_bytes'] for x in rows),
   prior_output_bytes=sum(int(x['SPI_bytes']) for x in old.values()),
   E1_extra_bytes=sum(x['E1_wire_delta'] for x in rows),
   E0_full=sum(x['E0_full'] for x in rows),E2_short=sum(x['E2_short'] for x in rows),
   status_polls=sum(x['status_polls'] for x in rows)),
  CPU=dict(commands=544,prior_commands=522,output_bytes=sum(x['CPU_output_bytes'] for x in rows),
   DMA_bytes=sum(x['CPU_DMA_bytes'] for x in rows),extra_clocks=sum(x['CPU_delta_clocks'] for x in rows),
   PPU_DMA_commands=sum(int(x['dma_bytes'])>0 for x in cpu),
   prior_PPU_DMA_commands=sum(int(x['dma_bytes'])>0 for x in oldcpu),
   extra_HDMA_WRAM_commands=sum(int(x['section'])==5 for x in cpu)-sum(int(x['section'])==5 for x in oldcpu),
   bank_fills=result['cpu01']['CPU']['zero_DMA_fills'],ROM_body=result['cpu01']['rom_body_bytes']),
  ARM=dict(standalone_size=pin(b/'arm01/size.log').read_text(),full_link_size=pin(q/'size-rom.log').read_text(),
   standalone_stack=result['arm01']['stack_observed'],live_stack=result['test01']['ARM']['stack_observed'],
   IRQ_bodies=len(result['test01']['ARM']['IRQ_cases']),prior_full_size=base['ARM_size']),
  warm_max=worst,warm_over=sum(x['budget_gap_ms']>0 for x in warm),
  warm_delta_range=[min(x['delta_ms'] for x in warm),max(x['delta_ms'] for x in warm)],
  frame954=next(x for x in rows if x['frame']==954),restricted_ROM=window,restricted_sequence=sequence,
  future_inline=dict(program_transmitted=False,program_executed_by_FPGA=False,
   warm_added_wire_range=[min(x['future_inline_extra_wire'] for x in warm),max(x['future_inline_extra_wire'] for x in warm)],
   warm_additive_sensitivity_range=[min(x['future_additive_sensitivity_ms'] for x in warm),max(x['future_additive_sensitivity_ms'] for x in warm)],
   scope='Standalone273 producer instructions plus future wire only; no new serializer/CRC cost, removed interpretation or retimed overlap.'),
  area=dict(new_RTL=False,new_MAP=False,verified_identical270_RTL=True,whole_comb=17680,comb_deficit=2272,
   reclaimed_comb=0,region_comb=6486,target_without_margin=4214,new_FPGA_RAM_bits=0),
  split_ARM_guards=17,retained_ARM_guards=24,RTL_guards=result['guards01']['guards'],
  RTL_fault_codes=fault_codes,
  full_path_ms=None,P2_selected=False,physical60fps=False,
  decision='Splitting resolves capacity using retained single-packet ownership; it is a bounded input policy, not a timing/area solution.',
  remaining=['Reference programs are not sent/executed by FPGA; common checked DMA/receipt descriptor binding is still mandatory.',
   'Source/query/header/map/receipt single executor and actual control removal remain unimplemented.',
   'Future inline kind/length view and actual CRC/credit/IRQ/SPI scheduling remain open.',
   'CPI1, IRQ service-boundary bodies and synthetic ROM contention are not full RUN/NVIC or measured hardware-cycle bounds.',
   'Actual forced-blank ordinary65816 trace is replayed; map/tile/final ACK are modeled, not a new whole65816 execution.',
   'No new FIT/STA/CDC/IO qualification, active-VBlank deadline or physical60fps claim.'],pins=pins)
 (d/'result.json').write_text(json.dumps(final,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({k:final[k] for k in ('CPU','ARM','warm_max','warm_over','restricted_ROM','future_inline','area')},indent=2))

if __name__=='__main__':main()
