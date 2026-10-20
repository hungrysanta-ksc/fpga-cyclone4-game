# SPDX-License-Identifier: MIT
"""Bind host single-consume RTL, retimed ARM/ROM/CPU trace and whole Lite MAP."""
from pathlib import Path
import argparse,collections,csv,difflib,json,re,sys
from nes_delta231 import BASE,ROOT,sha
from probe_nes_joint264 import packets
sys.path.insert(0,str(BASE/'.tools/arm259-python'))
from elftools.elf.elffile import ELFFile

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--base',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--run',default='test07');ap.add_argument('--guards',default='guards03')
 a=ap.parse_args();b=a.base.resolve();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
 pins={}
 def pin(p):pins[str(p)]=sha(p);return p
 def read(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
 def rows(p):return list(csv.DictReader(pin(p).open()))
 def events(p):return list(csv.reader(pin(p/'joint-events.csv').open()))
 def done(ev):return {int(x[1]):int(x[3])/1e9 for x in ev if x[0]=='frame_done'}
 prior=BASE/'probes/nes-joint274';p276=BASE/'probes/nes-joint276'
 selected=[a.run,'window01',a.guards,'guards04','board01'];r={n:read(b/n/'result.json') for n in selected}
 assert all(v['passed'] for v in r.values());q=b/a.run
 assert r[a.run]['CPI']==r['window01']['CPI']==1
 old={int(x['frame']):x for x in rows(prior/'analysis01/costs.csv')}
 prev={int(x['frame']):x for x in rows(p276/'analysis01/costs.csv')}
 oldrtl=read(prior/'test01/result.json')['rtl_hashes']
 changed=[n for n,h in r[a.run]['rtl_hashes'].items() if oldrtl.get(n)!=h]
 assert set(changed)=={'nes_core257.sv','nes_joint257.sv','nes_queue260.sv','nes_mux260.sv','nes_joint266.sv','nes_validator278.sv'}
 board_diffs={}
 for n,h in r[a.run]['rtl_hashes'].items():
  assert sha(pin(q/n))==h==sha(pin(b/'window01'/n))
  if n in r[a.guards]['rtl_hashes']:assert sha(pin(b/a.guards/n))==h
  if n in r['guards04']['rtl_hashes']:assert sha(pin(b/'guards04'/n))==h
 for n in changed:
  sim=pin(q/n).read_text();bd=pin(b/'board01'/n).read_text()
  def delta(x,y):
   return [v for v in difflib.unified_diff(x.splitlines(),y.splitlines(),n=0)
           if v.startswith(('+','-')) and not v.startswith(('+++','---'))]
  expected=[] if n=='nes_validator278.sv' else delta(
   pin(prior/'test01'/n).read_text(),pin(BASE/'probes/nes-joint270/board02'/n).read_text())
  # Both wrappers gained the same source-drained admission condition. It
  # shares a line with the pre-existing board-only tile_closed output.
  if n=='nes_joint266.sv':
   expected=[x.replace('.identity_valid(identity_valid)', '.identity_valid(identity_valid&&output_phase)') for x in expected]
  assert delta(sim,bd)==expected,n
  board_diffs[n]=expected
 for n in ['blocks.txt','commands.hex','stream.hex','expected.hex','hashes.hex','certs.hex',
           'CPU-bus.csv','CPU-timing.csv','CPU-ordinary.sfc','CPU-packets.hex','nes_output264.c']:
  assert pin(q/n).read_bytes()==pin(prior/'test01'/n).read_bytes(),n
 spi_guard=read(BASE/'probes/nes-joint275/spiguards01/result.json')
 for n,h in spi_guard['rtl_hashes'].items():assert sha(pin(q/n))==h
 arm_guard=read(prior/'armguards01/result.json')
 assert pin(q/'nes_output264.c').read_bytes()==pin(prior/'arm01/nes_output264.c').read_bytes()
 assert sha(pin(prior/'arm01/output.elf'))==arm_guard['ELF_sha256']
 with pin(q/'output.elf').open('rb') as f,pin(prior/'test01/output.elf').open('rb') as g:
  ef,eg=ELFFile(f),ELFFile(g);assert ef.header==eg.header and ef.num_sections()==eg.num_sections()
  for sec in ef.iter_sections():
   oldsec=eg.get_section_by_name(sec.name);assert sec.header==oldsec.header
   if sec.data()!=oldsec.data():
    assert sec.name=='.strtab' and sec['sh_flags']==0
    assert re.sub(rb'cc[A-Za-z0-9]{6}\.o',b'ccTEMP00.o',sec.data())==re.sub(rb'cc[A-Za-z0-9]{6}\.o',b'ccTEMP00.o',oldsec.data())
 ev=events(q);old_ev=events(p276/'test03');times=done(ev);assert len(times)==71
 cpu_rows=rows(q/'CPU-timing.csv')
 def parser(e,f,ordinary=False):
  return sum(int(x[3]) for x in e if x[0]=='parser' and int(x[1])==f and
             (not ordinary or int(x[2]) in [2,4,5,7,8]))/1e9
 assert sum(x[0]=='cpu267' for x in ev)==544 and sum(x[0]=='receipt' for x in ev)==2069
 assert max(int(x[2]) for x in ev if x[0]=='credits')==4
 sc={int(x['frame']):x for x in rows(q/'cycles.csv')}
 os={int(x['frame']):x for x in rows(prior/'test01/cycles.csv')}
 assert all(sc[f]['queries']==os[f]['queries'] for f in sc)
 assert sum(int(x.split()[2]) for x in (q/'blocks.txt').read_text().splitlines())==83240
 out=[];packet_count=0;oam_patterns=collections.Counter();raw_counts=collections.Counter()
 for f in range(905,976):
  expected=packets(pin(prior/f'arm01/frame{f}.packets'))
  actual=[bytes.fromhex(x['tx'])[1:-2] for x in read(q/f'arm{f}.json')['transfers'] if x['tx'].startswith('e1')]
  assert actual==expected;packet_count+=len(actual)
  oam_patterns.update(p[16:].hex() for p in actual if p[0]==8 and p[1]==4)
  raw_counts.update(p[36] for p in actual if p[0]==13)
  ct=collections.Counter();wire=collections.Counter();instructions=0
  for x in ev:
   if x[0]=='arm267' and int(x[1])==f:
    ct[int(x[2])]+=1;wire[int(x[2])]+=int(x[3]);instructions+=int(x[5])
  total=int(sc[f]['total'])*45.454/1e6+times[f]
  cpu=[x for x in cpu_rows if int(x['serial'])==f-904]
  pattern=[x for x in cpu if int(x['op'])==8 and int(x['section'])==4]
  assert len(pattern)==1
  prev_transactions=sum(int(prev[f][k]) for k in ['E0_full','E2_short','E8','E9','EA'])+len(actual)
  charged_delta=(sum(wire.values())-int(prev[f]['SPI_bytes']))*8/2625+\
   (instructions-int(prev[f]['ARM_IRQ_event_instructions']))/84000+\
   (sum(ct.values())-prev_transactions)*.008
  out.append(dict(frame=f,source_ms=int(sc[f]['total'])*45.454/1e6,
   output_schedule_ms=times[f],diagnostic_serial_ms=total,
   prior274_ms=float(old[f]['diagnostic_serial_ms']),delta274_ms=total-float(old[f]['diagnostic_serial_ms']),
   prior276_ms=float(prev[f]['diagnostic_serial_ms']),delta276_ms=total-float(prev[f]['diagnostic_serial_ms']),
   budget_gap_ms=total-1000/60,E1_wire=wire[225],E0_full=ct[224],E2_short=ct[226],
   E8=ct[232],E9=ct[233],EA=ct[234],SPI_bytes=sum(wire.values()),ARM_IRQ_event_instructions=instructions,
   prior276_E2=int(prev[f]['E2_short']),post_ACK_parser_ms=parser(ev,f),
   prior276_post_ACK_parser_ms=parser(old_ev,f),ordinary_parser_ms=parser(ev,f,True),
   prior276_ordinary_parser_ms=parser(old_ev,f,True),
   wire_instruction_transaction_delta276_ms=charged_delta,
   remaining_schedule_delta276_ms=total-float(prev[f]['diagnostic_serial_ms'])-charged_delta))
  out[-1].update(retained_general_CPU_master_clocks=sum(int(x['total_clocks']) for x in cpu),
   retained_OAM_pattern4_master_clocks=int(pattern[0]['total_clocks']),
   retained_OAM_after_read_before_DMA_setup_master_clocks=
    int(pattern[0]['service_clocks'])-int(pattern[0]['dma_setup_service_clocks']))
 assert packet_count==1231
 assert oam_patterns=={'00f00000':71} and raw_counts=={2:71}
 with (d/'costs.csv').open('w',newline='') as h:
  w=csv.DictWriter(h,fieldnames=list(out[0]),lineterminator='\n');w.writeheader();w.writerows(out)
 wr=events(b/'window01');ws={int(x['frame']):x for x in rows(b/'window01/cycles.csv')}
 pw={x['frame']:x for x in read(p276/'analysis01/result.json')['restricted_ROM']}
 window=[]
 for f,t in done(wr).items():
  total=int(ws[f]['total'])*45.454/1e6+t
  lines=[x for x in wr if x[0]=='arm267' and int(x[1])==f]
  window.append(dict(frame=f,diagnostic_serial_ms=total,prior276_ms=pw[f]['diagnostic_serial_ms'],
   delta276_ms=total-pw[f]['diagnostic_serial_ms'],budget_gap_ms=total-1000/60,
   E2=sum(int(x[2])==226 for x in lines),SPI_bytes=sum(int(x[3]) for x in lines)))
 def end(e):return max(int(x[2]) for x in e if x[0]=='frame_done')/1e9
 def mapping(folder):
  s=pin(folder/'output_files/board.map.summary').read_text();m={}
  for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),
                  ('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]:
   m[k]=int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',s).group(1).replace(',',''))
  rpt=pin(folder/'output_files/board.map.rpt').read_text();own={}
  for line in rpt.splitlines():
   fields=[v.strip() for v in line.split(';')]
   if len(fields)==14 and re.fullmatch(r'\d+ \(\d+\)',fields[2]):
    own[fields[10]]={k:int(re.search(r'\((\d+)\)',fields[i]).group(1)) for k,i in [('comb',2),('FF',3)]}
  assert {k:sum(v[k] for v in own.values()) for k in ['comb','FF']}=={k:m[k] for k in ['comb','FF']}
  return m,own,rpt
 m,own,rpt=mapping(b/'board01');m276,o276,_=mapping(p276/'board01')
 phase_ram=[line for line in rpt.splitlines() if 'nes_joint257:core|altsyncram:memory_rtl_0' in line and 'True Dual Port' in line]
 assert len(phase_ram)==1 and '1024' in phase_ram[0] and '8192' in phase_ram[0]
 fsm_paths=['nes_core257:encoder|state','nes_validator278:validator|state',
            'nes_output260:flow|state','nes_output260:flow|tap_state278']
 assert all(any('State Machine - ' in line and p in line for line in rpt.splitlines()) for p in fsm_paths)
 m274,o274,_=mapping(BASE/'probes/nes-joint270/board02')
 changes=[dict(path=k,before=o276.get(k,dict(comb=0,FF=0)),after=own.get(k,dict(comb=0,FF=0)))
          for k in sorted(own.keys()|o276.keys()) if own.get(k)!=o276.get(k)]
 core=pin(q/'nes_core257.sv').read_text();flow=pin(q/'nes_mux260.sv').read_text()
 assert 'P_LOAD:' not in core and 'V_RWRITE:' not in core
 assert not re.search(r'nes_native_mailbox206.*(?:consumed|receipt)\(',flow)
 assert 'ordinary_mode&&(data_command278||header[0]==7)' in flow
 counts=re.search(r'COUNTS278 tap=(\d+) mask=(\d+) provisional=(\d+) orderedACK=(\d+)',pin(q/'vsim.log').read_text())
 assert counts
 counters=dict(zip(['original_bus_body_reads','deferred_source_mask_writes','provisional_raw_CRCs','ordered_ACKs'],map(int,counts.groups())))
 assert counters==dict(original_bus_body_reads=17277,deferred_source_mask_writes=574*71,
                       provisional_raw_CRCs=32,ordered_ACKs=793),counters
 region=[k for k in own if k.endswith(('nes_core257:encoder','nes_validator278:validator','nes_output260:flow','nes_queue260:queue'))]
 assert len(region)==4
 region_comb=sum(own[k]['comb'] for k in region)
 assert sorted(r[a.guards]['guards'])==list(range(1,53))
 assert r['guards04']['guards']==[1,2,3,4,20,21,22,23,24,27,28,29]
 assert all('COUNTS278' in pin(b/'guards04'/f'guard{i}.log').read_text() for i in r['guards04']['guards'])
 warm=[x for x in out if x['frame']>=907]
 result=dict(passed=True,stage=278,scope=__doc__,selected=selected,frames=71,packets=1231,
  source_bytes=83240,map_ranges=2069,map_bytes=13406,map_tile_DMA_bytes=26350,
  metadata_per_frame=8570,receipt_per_frame=754,CRC_per_frame=64,ordinary_CPU_trace_commands=544,
  original_wire_and_ARM_loaded_sections_identical274=True,source_query_prefetch_preserved=True,
  source_cycle_deltas274={k:dict(min=min(int(sc[f][k])-int(os[f][k]) for f in sc),
                               max=max(int(sc[f][k])-int(os[f][k]) for f in sc))
                         for k in ['total','prepare','blocked','ackwait','transfer','overlap']},
  changed_RTL=changed,board_binding=board_diffs,counters=counters,
  raw_counts=dict(raw_counts),raw_zero_transition_executed=False,
  retained_OAM_repeat4_patterns=dict(oam_patterns),
  warm_max=max(warm,key=lambda x:x['diagnostic_serial_ms']),
  warm_over=sum(x['diagnostic_serial_ms']>1000/60 for x in warm),
  over_frames=[x['frame'] for x in warm if x['diagnostic_serial_ms']>1000/60],
  frame954=next(x for x in out if x['frame']==954),restricted_ROM=window,
  restricted_sequence=dict(current_end_ms=end(wr),prior276_end_ms=end(events(p276/'window01'))),
  SPI=dict(total=sum(x['SPI_bytes'] for x in out),E2=sum(x['E2_short'] for x in out)),
  ARM=dict(CPI=1,clock_MHz=84,loaded_sections_identical274=True,
           observed_stack=r[a.run]['ARM']['stack_observed'],
           IRQ_bodies=len(r[a.run]['ARM']['IRQ_cases']),full_RUN=False),
  ROM_observations=dict(normal=[x for x in ev if x[0] in ('rom267','romwait267')],
                        restricted=[x for x in wr if x[0] in ('rom267','romwait267')],
   note='Counters except tile byte count are cumulative at ROM end markers. Upstream tile wait/core_block show contention; ready-gated denied counter is not a contention measure. These counters overlap the measured schedule.'),
  MAP=dict(current=m,prior276=m276,prior274=m274,delta276={k:m[k]-m276[k] for k in m},
           delta274={k:m[k]-m274[k] for k in m},comb_deficit=m['comb']-15408,own_changes=changes,
           source_validator_host_queue_comb=region_comb,retained_other_comb=m['comb']-region_comb,
           region_budget_if_others_fixed=15408-m['comb']+region_comb,
           phase_RAM_summary=phase_ram[0],extracted_FSM_paths=fsm_paths,
           fixed_dual_clock_phase_RAM=True,FIT=False,STA=False),
  guards=r[a.guards]['guards'],stronger_ACK_counter_guards=r['guards04']['guards'],
  full_path_ms=None,full_RUN=False,actual_SNES_live=False,
  reused_SPI_guards=spi_guard['log'],reused_ARM_guards=arm_guard,
  P2_selected=False,physical=False,input_hashes=pins,script_sha256=sha(Path(__file__)))
 (d/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:result[k] for k in ['passed','warm_max','restricted_ROM','restricted_sequence','counters','SPI']},indent=2))
 print(json.dumps({k:result['MAP'][k] for k in ['current','delta276','delta274','comb_deficit']},indent=2))

if __name__=='__main__':main()
