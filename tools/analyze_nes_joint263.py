# SPDX-License-Identifier: MIT
"""Hash-bound ordinary bridge and paired65816 common-context costs.

The diagnostic serial sum is not a full-frame bound. CPU/RTL RPC clocks are
separate. Native C execution is not charged as target65816/ARM execution.
"""
import argparse,csv,hashlib,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_joint263 import sources
from probe_nes_common263 import common_sources
from probe_nes_joint261 import packets

def cpu_service(path,expected=64):
 rows=[list(map(int,r)) for r in csv.reader(path.open())];intervals=[];pending=None;last_consume=None;gaps={};batch=False
 for seq,op,addr,value,t in rows:
  if op==0 and addr==0x6040:
   if last_consume is not None:gaps[len(intervals)-1]=t-last_consume;last_consume=None
   if value==1:assert pending is None;pending=t;batch=False
  if op==0 and addr==0x6053:batch=True
  if op==1 and addr==0x6050:
   assert pending is not None;intervals.append(dict(ready_to_consume=t-pending,new_batch=batch));pending=None;last_consume=t
 assert len(intervals)==expected and len(gaps)==expected and pending is None
 for i,r in enumerate(intervals):r['after_consume_to_first_poll']=gaps[i];r['service_clocks']=r['ready_to_consume']+gaps[i]
 return dict(ranges=intervals,service_clocks=sum(r['service_clocks'] for r in intervals),
  identity_reads=sum(op==0 and addr in [0x6041,0x6046,0x6047] for _,op,addr,_,_ in rows),
  token_reads=sum(op==0 and 0x6048<=addr<=0x604b for _,op,addr,_,_ in rows),
  count_reads=sum(op==0 and addr==0x6053 for _,op,addr,_,_ in rows),
  token_writes=sum(op==1 and 0x604c<=addr<=0x604f for _,op,addr,_,_ in rows))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve();assert not out.exists();out.mkdir(parents=True)
 base=BASE/'probes/nes-joint263';pins={}
 def pin(path):pins[path.relative_to(BASE).as_posix()]=sha(path);return path
 def read(name):return json.loads(pin(base/name/'result.json').read_text(encoding='utf-8'))
 test=read('test03');guard=read('guards03');cg=read('cguard02');cpug=read('cpuguard01');maps=read('map01');commonmap=read('map02');ref=read('cpuref01');cached=read('cpucache01');warmref=read('cpuwarmref01');warmcache=read('cpuwarmcache01')
 assert test['passed'] and test['frames']==71 and guard['passed'] and guard['guards']==list(range(1,9))
 assert cg['passed'] and len(cg['cases'])==16 and cpug['passed'] and len(cpug['cases'])==8
 assert len(cg['tile_event_vectors'])==3
 for name,res in [('test03',test),('guards03',guard),('map01',maps),('cpuref01',ref),('cpucache01',cached),('map02',commonmap),('cpuwarmref01',warmref),('cpuwarmcache01',warmcache)]:
  assert res['passed']
  expected=common_sources() if name in ['cpuref01','cpucache01','map02','cpuwarmref01','cpuwarmcache01'] else sources()
  for n,h in res['rtl_hashes'].items():assert sha(pin(base/name/n))==h,(name,n)
  for n,s in expected.items():assert hashlib.sha256(s.encode()).hexdigest()==res['rtl_hashes'][n],(name,n)
  for path in (base/name).glob('*.log'):pin(path)
 for i in range(1,9):assert f'PASS BRIDGE263 GNEG={i}' in pin(base/'guards03'/f'guard{i}.log').read_text()
 assert guard['TB_sha256']==sha(pin(base/'guards03/joint263_tb.sv'))
 assert maps['test_sha256']==sha(pin(base/'test02/result.json'))
 assert commonmap['test_sha256']==sha(pin(base/'cpuref01/result.json'))
 for name in ['map01','map02']:pin(base/name/'output_files/joint.map.rpt');pin(base/name/'output_files/joint.map.summary')
 for name,r in [('test03',test),('cpuref01',ref),('cpucache01',cached),('cpuwarmref01',warmref),('cpuwarmcache01',warmcache)]:
  for key,h in r['input_hashes'].items():
   path=Path(key) if Path(key).is_absolute() else BASE/key
   assert sha(pin(path))==h,(name,key)
 assert sha(pin(ROOT/'tools/nes_producer263.c'))==cg['source_sha256']==sha(pin(base/'test03/nes_producer263.c'))
 assert cg['DLL_sha256']==sha(pin(base/'test02/producer263.dll'))
 assert cpug['source_sha256']==sha(pin(ROOT/'tools/probe_nes_common263.py'))
 flat={}
 for line in pin(base/'test03/blocks.txt').read_text().splitlines():
  frame,token,n,b=line.split();flat.setdefault(int(frame),bytearray()).extend(bytes.fromhex(b))
 assert len(flat)==71
 for frame,data in flat.items():
  prior=BASE/'probes/nes-joint249/blocktest03';n=int(pin(prior/f'frame{frame}.meta').read_text().split()[0]);assert data==bytes.fromhex(pin(prior/f'frame{frame}.expected.hex').read_text())[:n]
 ev=list(csv.reader(pin(base/'test03/joint-events.csv').open()));done={int(r[1]):int(r[3])/1e9 for r in ev if r[0]=='frame_done'}
 consumers={int(r[1]):list(map(int,r[2:])) for r in ev if r[0]=='consumer'}
 srcrows={int(r['frame']):r for r in csv.DictReader(pin(base/'test03/cycles.csv').open())}
 prior_ev=list(csv.reader(pin(BASE/'probes/nes-joint262/test05/joint-events.csv').open()));prior_times={int(r[1]):int(r[3])/1e9 for r in prior_ev if r[0]=='frame_done'}
 arm=json.loads(pin(BASE/'probes/nes-joint262/arm01/result.json').read_text());armrows={r['frame']:r for r in arm['frames']}
 rows=[];batch_packets=map_ranges=map_bytes=packet_count=0
 for f in range(905,976):
  pp=packets(pin(BASE/f'probes/nes-joint262/arm01/frame{f}.packets'))
  assert bytes.fromhex(pin(base/f'test03/all{f}.hex').read_text())==b''.join(pp)
  lengths=[int(n,16) for n in pin(base/f'test03/all{f}.lens').read_text().split()];assert lengths==[len(pp),*[len(p) for p in pp]]
  expected_ordinary=sum(p[0] not in [1,13,14] for p in pp);assert consumers[f][1]==expected_ordinary
  dma=sum(int.from_bytes(p[14:16],'little') for p in pp if p[0]==7)
  for p in pp:
   if p[0]!=14:continue
   batch_packets+=1;map_ranges+=p[20];at=21
   for _ in range(p[20]):n=p[at+2];at+=3+n;dma+=n;map_bytes+=n
   assert at==len(p)
  assert dma==consumers[f][2];packet_count+=len(pp)
  source_ms=int(srcrows[f]['total'])*45.454/1e6
  poll_bytes=armrows[f]['status_reads']*24;cpu_ms=armrows[f]['ARM_instructions']/84000
  rows.append(dict(frame=f,source_ms=source_ms,output_model_ms=done[f],diagnostic_serial_ms=source_ms+done[f],
   prior262_output_model_ms=prior_times[f],added_functionality_ms=done[f]-prior_times[f],consumer_events=consumers[f][0],ordinary_packets=expected_ordinary,DMA_bytes=dma,
   output_E1_bytes=sum(len(p)+3 for p in pp),prior_ARM_model_poll_bytes=poll_bytes,prior_ARM_model_CPI1_ms=cpu_ms,
   serial_plus_prior_poll_and_CPI1_sensitivity_ms=source_ms+done[f]+poll_bytes*8/2625+cpu_ms))
 assert (batch_packets,map_ranges,map_bytes)==(124,2069,13406)
 cpu={}
 for name,result in [('reference',ref),('cached',cached)]:
  folder='cpuref01' if name=='reference' else 'cpucache01'
  assert result['cpu']['passed'] and result['cpu']['dma_bytes']==4096 and result['cpu']['ranges']==64
  assert sha(pin(base/folder/'joint.sfc'))==result['rom_sha256']
  cpu[name]=cpu_service(pin(base/folder/'cpu-bus.csv'));cpu[name].update(ROM_body_bytes=result['rom_body_bytes'],final_ack_master=result['cpu']['final_ack_master'])
  pin(base/folder/'rtl-dma.csv');pin(base/folder/'cpu-result.json')
 assert cpu['reference']['identity_reads']==192 and cpu['cached']['identity_reads']==66
 assert cpu['reference']['token_reads']==260 and cpu['cached']['token_reads']==92
 assert cpu['reference']['token_writes']==cpu['cached']['token_writes']==260 and cpu['cached']['count_reads']==22
 cpu['saved_service_clocks']=cpu['reference']['service_clocks']-cpu['cached']['service_clocks']
 cpu['saved_service_ms']=cpu['saved_service_clocks']/21477.272727
 warm={}
 for name,result in [('reference',warmref),('cached',warmcache)]:
  folder='cpuwarmref01' if name=='reference' else 'cpuwarmcache01'
  assert result['cpu']['passed'] and result['cpu']['dma_bytes']==40 and result['cpu']['ranges']==7
  assert sha(pin(base/folder/'joint.sfc'))==result['rom_sha256']
  warm[name]=cpu_service(pin(base/folder/'cpu-bus.csv'),7)
  warm[name].update(ROM_body_bytes=result['rom_body_bytes'],final_ack_master=result['cpu']['final_ack_master'])
  pin(base/folder/'rtl-dma.csv');pin(base/folder/'cpu-result.json');pin(base/folder/'joint262_tb.sv');pin(base/folder/'capture.lua')
 assert warm['reference']['identity_reads']==21 and warm['cached']['identity_reads']==3
 assert warm['reference']['token_reads']==32 and warm['cached']['token_reads']==8 and warm['cached']['count_reads']==1
 assert warm['reference']['token_writes']==warm['cached']['token_writes']==32
 warm['saved_service_clocks']=warm['reference']['service_clocks']-warm['cached']['service_clocks'];warm['saved_service_ms']=warm['saved_service_clocks']/21477.272727
 cpu['warm907']=warm
 def area(r):
  s=r['summary'];assert 'Lite Edition' in s
  return {k:int(re.search(pattern+r'\s*:\s*([\d,]+)',s).group(1).replace(',','')) for k,pattern in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
 oldarea=dict(LE=7216,comb=5755,FF=2806,RAM_bits=90368);fullarea=area(maps);smallarea=area(commonmap)
 hierarchy={}
 for line in (base/'map01/output_files/joint.map.rpt').read_text().splitlines():
  fields=[v.strip() for v in line.split(';')]
  if len(fields)>5 and fields[1] in ['|nes_joint257:core|','|nes_output260:flow|']:
   hierarchy[fields[1]]={k:int(re.match(r'\d+',v).group()) for k,v in zip(['comb','FF','RAM_bits'],fields[2:5])}
 assert len(hierarchy)==2
 previous=json.loads(pin(ROOT/'analysis/joint262-verification.json').read_text())['replacement_ledger']['old_excluding_lease']
 replacement={k:sum(v[k] for v in hierarchy.values()) for k in previous}
 ledger=dict(old_excluding_lease=previous,new_excluding_lease_and_top=replacement,arithmetic_delta={k:replacement[k]-previous[k] for k in previous},same_synthesis_boundary=False,proven_whole_LE_reclaim=0)
 result=dict(passed=True,stage='NES263',frames=71,source_bytes=sum(map(len,flat.values())),packets=packet_count,batches=batch_packets,map_ranges=map_ranges,map_bytes=map_bytes,
  consumer_events=sum(r['consumer_events'] for r in rows),ordinary_packets=sum(r['ordinary_packets'] for r in rows),DMA_bytes=sum(r['DMA_bytes'] for r in rows),manifest_bytes=71*422,
  C_guards=len(cg['cases']),RTL_guards=len(guard['guards']),CPU_mock_guards=len(cpug['cases']),CPU=cpu,
  MAP=dict(prior262=oldarea,bridge_and_common=fullarea,common_only=smallarea,bridge_delta={k:fullarea[k]-oldarea[k] for k in oldarea},common_delta={k:smallarea[k]-oldarea[k] for k in oldarea}),
  replacement_ledger=ledger,
  warm_max_output=max(rows[2:],key=lambda r:r['output_model_ms']),warm_max_serial=max(rows[2:],key=lambda r:r['diagnostic_serial_ms']),
  heavy=[r for r in rows if r['frame'] in [905,906,907,954,955,963,970]],
  full_path_ms=None,whole_board_margin=None,whole_FIT=False,P2_selected=False,physical60fps=False,
  decision='batch context is conditional: cold short batches regress; evaluate warm long batches. Do not select byte-event bridge as60fps implementation',
  limitations=['C ordinary executor is native DPI; its event queue/metadata/touched arrays are verification storage, not a target allocation.',
   'Tile bytes and ARM packet plans remain recorded inputs; full N5/planner/RUN/IRQ and real ROM contention are absent.',
   'All E1 packets replay unchanged but ARM E0 polling/refill is not executed in the71-frame RTL run.',
   '900-clock DMA setup,400ns bus byte and560ns ordinary byte are allocations; native C decoder cycles are not charged.',
   'Paired65816 test uses262 non-map fixture producers. It is not a coupled full ordinary65816 implementation.',
   'Warm907 replays905/906 with the bus model and seeds prior905 VRAM before its first real CPU DMA; not continuous full-game execution.',
   'CPU service includes post-consume software token increment up to the first next poll; polling waits and VBlank are separate.',
   'Prior ARM poll/CPI sensitivity is serial and unmatched endpoint behavior, not a bound or retimed full-frame schedule.',
   'CRC is not authentication or collision-free proof; FIT/STA/CDC/IO and490LE40LAB wholeboard deficit remain open.'],input_hashes=pins)
 with (out/'costs.csv').open('w',newline='',encoding='utf-8') as fd:w=csv.DictWriter(fd,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({k:result[k] for k in ['frames','source_bytes','consumer_events','ordinary_packets','DMA_bytes','MAP','warm_max_serial']}));print(json.dumps({k:v for k,v in cpu.items() if k.startswith('saved')}))

if __name__=='__main__':main()
