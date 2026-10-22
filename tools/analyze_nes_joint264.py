# SPDX-License-Identifier: MIT
"""Compare identical integrated boundaries; serial sensitivities are not WCET."""
import argparse,csv,hashlib,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_joint264 import sources
from probe_nes_joint261 import packets


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--test',default='test04');p.add_argument('--guards',default='guards01');a=p.parse_args()
 out=a.out.resolve();assert not out.exists();out.mkdir(parents=True);base=BASE/'probes/nes-joint264';pins={}
 def pin(path):pins[path.relative_to(BASE).as_posix()]=sha(path);return path
 def read(path):return json.loads(pin(path).read_text(encoding='utf-8'))
 test=read(base/a.test/'result.json');guard=read(base/a.guards/'result.json');m=read(base/'map01/result.json');arm=read(base/'arm01/result.json');ag=read(base/'armguard01/result.json')
 assert test['passed'] and test['frames']==71 and guard['passed'] and guard['guards']==list(range(1,20))
 assert ag['passed'] and len(ag['cases'])==12 and len(ag['preflight'])==6
 for name,res in [(a.test,test),(a.guards,guard),('map01',m)]:
  assert res['passed']
  for n,h in res['rtl_hashes'].items():assert sha(pin(base/name/n))==h,(name,n)
  for n,s in sources().items():assert hashlib.sha256(s.encode()).hexdigest()==res['rtl_hashes'][n],(name,n)
  for path in (base/name).glob('*.log'):pin(path)
 for i in guard['guards']:assert f'PASS DIRECT264 GNEG={i}' in pin(base/a.guards/f'guard{i}.log').read_text()
 assert m['test_sha256']==sha(pin(base/a.test/'result.json'))
 for path,h in test['input_hashes'].items():assert sha(pin(BASE/path))==h,path
 assert arm['source_sha256']==sha(pin(ROOT/'tools/nes_output264.c'))
 assert arm['ELF_sha256']==ag['ELF_sha256']==sha(pin(base/'arm01/output.elf'))
 old=read(ROOT/'analysis/joint263-verification.json');oldarm=read(BASE/'probes/nes-joint262/arm01/result.json')
 armrows={r['frame']:r for r in arm['frames']};oldarms={r['frame']:r for r in oldarm['frames']}
 oldrows={int(r['frame']):r for r in csv.DictReader(pin(ROOT/'analysis/joint263-costs.csv').open())}
 srcrows={int(r['frame']):r for r in csv.DictReader(pin(base/a.test/'cycles.csv').open())}
 ev=list(csv.reader(pin(base/a.test/'joint-events.csv').open()));done={int(r[1]):int(r[3])/1e9 for r in ev if r[0]=='frame_done'}
 consumers={int(r[1]):list(map(int,r[2:])) for r in ev if r[0]=='consumer'}
 credits=[int(r[2]) for r in ev if r[0]=='credits'];assert len(credits)==71 and max(credits)==4
 parser={f:0 for f in range(905,976)}
 for r in ev:
  if r[0]=='parser':parser[int(r[1])]+=int(r[3])/1e9
 assert len(done)==len(consumers)==71 and sum(r[0]=='receipt' for r in ev)==2069
 flat={}
 for line in pin(base/a.test/'blocks.txt').read_text().splitlines():
  frame,token,n,b=line.split();flat.setdefault(int(frame),bytearray()).extend(bytes.fromhex(b))
 assert len(flat)==71
 for frame,data in flat.items():
  prior=BASE/'probes/nes-joint249/blocktest03';n=int(pin(prior/f'frame{frame}.meta').read_text().split()[0]);assert data==bytes.fromhex(pin(prior/f'frame{frame}.expected.hex').read_text())[:n]
 rows=[];batches=ranges=mapbytes=0
 for f in range(905,976):
  pp=packets(pin(base/f'arm01/frame{f}.packets'));prior=packets(pin(BASE/f'probes/nes-joint262/arm01/frame{f}.packets'))
  assert bytes.fromhex(pin(base/a.test/f'all{f}.hex').read_text())==b''.join(pp)
  assert [int(n,16) for n in pin(base/a.test/f'all{f}.lens').read_text().split()]==[len(pp),*[len(p) for p in pp]]
  assert pp[-1][0]==3 and len(pp[-1])==16 and sum(p[0]==15 for p in pp)==1
  phase=0
  for q in pp:
   if q[0]==15:assert phase==0;phase=1
   elif q[0] in (10,11):assert phase==1
   elif q[0]==3:assert phase==1;phase=2
   else:assert phase==0
  dma=sum(int.from_bytes(p[14:16],'little') for p in pp if p[0]==7)
  for q in pp:
   if q[0]!=14:continue
   batches+=1;ranges+=q[20];at=21
   for _ in range(q[20]):n=q[at+2];at+=3+n;dma+=n;mapbytes+=n
   assert at==len(q)
  assert consumers[f]==[0,sum(p[0] not in (1,13,14) for p in pp),dma]
  wire=sum(len(p)+3 for p in pp);previous_wire=sum(len(p)+3 for p in prior);assert wire-previous_wire==19
  ar=armrows[f];oa=oldarms[f];assert ar['status_reads']-oa['status_reads']==1 and ar['SPI_bytes']-oa['SPI_bytes']==43
  source=int(srcrows[f]['total'])*45.454/1e6;cpu=ar['ARM_instructions']/84000;poll=ar['status_reads']*24*8/2625
  previous=float(oldrows[f]['output_model_ms']);oldserial=float(oldrows[f]['serial_plus_prior_poll_and_CPI1_sensitivity_ms'])
  rows.append(dict(frame=f,source_ms=source,output_model_ms=done[f],prior263_output_ms=previous,output_saved_ms=previous-done[f],
   diagnostic_serial_ms=source+done[f],ARM_endpoint_poll_bytes=ar['status_reads']*24,ARM_CPI1_ms=cpu,
   serial_with_unmatched_ARM_sensitivity_ms=source+done[f]+poll+cpu,prior263_serial_sensitivity_ms=oldserial,
   serial_sensitivity_saved_ms=oldserial-source-done[f]-poll-cpu,ARM_extra_instructions=ar['ARM_instructions']-oa['ARM_instructions'],
   post_ACK_parser_ms=parser[f],extra_E1_bytes=19,extra_status_bytes=24,E1_bytes=wire,DMA_bytes=dma,ordinary_packets=consumers[f][1],SNES_echo_events=0))
 assert (batches,ranges,mapbytes)==(124,2069,13406)
 s=m['summary'];assert 'Lite Edition' in s
 area={k:int(re.search(pattern+r'\s*:\s*([\d,]+)',s).group(1).replace(',','')) for k,pattern in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
 oldarea=old['MAP']['bridge_and_common'];hierarchy={}
 report=pin(base/'map01/output_files/joint.map.rpt')
 for line in report.read_text().splitlines():
  fields=[v.strip() for v in line.split(';')]
  if len(fields)>5 and fields[1] in ['|nes_joint257:core|','|nes_output260:flow|']:
   hierarchy[fields[1]]={k:int(re.match(r'\d+',v).group()) for k,v in zip(['comb','FF','RAM_bits'],fields[2:5])}
 assert len(hierarchy)==2
 fsm_names=re.findall(r'State Machine - ([^\r\n]+)',report.read_text())
 oldreport=pin(BASE/'probes/nes-joint263/map01/output_files/joint.map.rpt')
 fsm=dict(core_extracted=any('nes_core257:encoder|state' in n for n in fsm_names),
  output_state_extracted=any(n.endswith('nes_output260:flow|state') for n in fsm_names),
  prior263_output_state_extracted='State Machine - |nes_joint263|nes_output260:flow|state' in oldreport.read_text(),
  structural_observation='state <= after_event is a register-derived next-state assignment; possible extraction obstacle, not isolated attribution of943LE',
  extractor_diagnostic_reason=None)
 assert fsm['core_extracted'] and not fsm['output_state_extracted'] and fsm['prior263_output_state_extracted']
 oldledger=old['replacement_ledger']['old_excluding_lease'];newledger={k:sum(v[k] for v in hierarchy.values()) for k in oldledger}
 result=dict(passed=True,stage='NES264',frames=71,source_bytes=sum(map(len,flat.values())),batches=batches,map_ranges=ranges,map_bytes=mapbytes,
  DMA_bytes=sum(r['DMA_bytes'] for r in rows),ordinary_packets=sum(r['ordinary_packets'] for r in rows),SNES_echo_events=0,prior_echo_events=old['consumer_events'],
  RTL_guards=len(guard['guards']),max_queue_credit=max(credits),ARM_guards=18,ARM=dict(text=2472,static_BSS=312,observed_stack=arm['stack_observed'],text_delta=152,stack_delta=8,extra_SPI_bytes=43,
   instruction_delta_min=min(r['ARM_extra_instructions'] for r in rows),instruction_delta_max=max(r['ARM_extra_instructions'] for r in rows)),
  MAP=dict(prior263=oldarea,direct264=area,FSM=fsm,delta={k:area[k]-oldarea[k] for k in area},hierarchy=hierarchy),
  replacement_ledger=dict(old_excluding_lease=oldledger,new_excluding_lease_and_top=newledger,arithmetic_delta={k:newledger[k]-oldledger[k] for k in oldledger},same_synthesis_boundary=False,proven_whole_LE_reclaim=0),
  warm_max_output=max(rows[2:],key=lambda r:r['output_model_ms']),warm_max_serial=max(rows[2:],key=lambda r:r['diagnostic_serial_ms']),
  warm_max_serial_sensitivity=max(rows[2:],key=lambda r:r['serial_with_unmatched_ARM_sensitivity_ms']),
  min_warm_output_saved_ms=min(r['output_saved_ms'] for r in rows[2:]),heavy=[r for r in rows if r['frame'] in (905,906,907,954,955,963,970)],
  decision='Time improves; logic increases943LE. Keep as executable direct-payload reference, not selected as60fps implementation.',full_path_ms=None,whole_board_margin=None,whole_FIT=False,P2_selected=False,physical60fps=False,
  limitations=['71-frame RTL replays actual Cortex-M4 E1 bytes; E0 refill, full RUN/IRQ and ROM contention are not coupled.',
   'Ordinary execution is native C plus bus service allocation, not actual65816. ACK attests execution; sequential reads alone do not prove PPU writes.',
   '900 master-clock DMA setup,400ns bus byte,560ns ordinary byte are allocations. Native C decode cycles are uncharged.',
   'Final display ACK is a bus model without VBlank. New requirements/fence target65816 display context and RAM are not implemented.',
   'C oracle metadata/event arrays/206B saved requirements are verification storage, not target allocation.',
   'Partial scroll prefix and partial raw-tail granules are rejected by this candidate; no arbitrary scatter update support claim.',
   'ARM serial sensitivity uses a separate endpoint poll model and CPI1; it is not a retimed critical path, upper bound or measured frame.',
   'Source/core and transport still use shared CRC ownership; no full FIT/STA/CDC/IO,490LE40LAB baseline shortage remains.',
   'CRC is not authentication or collision-free proof.'],input_hashes=pins)
 with (out/'costs.csv').open('w',newline='',encoding='utf-8') as fd:
  w=csv.DictWriter(fd,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({k:result[k] for k in ['MAP','warm_max_output','warm_max_serial_sensitivity','min_warm_output_saved_ms']}))


if __name__=='__main__':main()
