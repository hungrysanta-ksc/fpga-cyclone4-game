# SPDX-License-Identifier: MIT
"""Same-boundary time/area evidence; retain unmatched ARM costs as sensitivity."""
import argparse,csv,hashlib,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_joint265 import sources
from probe_nes_joint261 import packets


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--guards',default='guards01');a=p.parse_args()
 out=a.out.resolve();assert not out.exists();out.mkdir(parents=True);base=BASE/'probes/nes-joint265';pins={}
 def pin(path):pins[path.relative_to(BASE).as_posix()]=sha(path);return path
 def read(path):return json.loads(pin(path).read_text(encoding='utf-8'))
 test=read(base/'test04/result.json');guard=read(base/a.guards/'result.json');m=read(base/'map01/result.json');cold=read(base/'test03/result.json')
 assert test['passed'] and test['frames']==71 and guard['passed'] and guard['guards']==list(range(1,30))
 for name,res in [('test04',test),(a.guards,guard),('map01',m),('test03',cold)]:
  assert res['passed']
  for n,h in res['rtl_hashes'].items():assert sha(pin(base/name/n))==h,(name,n)
  for n,s in sources().items():assert hashlib.sha256(s.encode()).hexdigest()==res['rtl_hashes'][n],(name,n)
  for path in (base/name).glob('*.log'):pin(path)
 assert m['test_sha256']==sha(base/'test03/result.json')
 for i in guard['guards']:assert f'PASS DIRECT265 GNEG={i}' in (base/a.guards/f'guard{i}.log').read_text()
 for path,h in test['input_hashes'].items():assert sha(pin(BASE/path))==h,path
 prior=read(ROOT/'analysis/joint264-verification.json')
 oldrows={int(r['frame']):r for r in csv.DictReader(pin(ROOT/'analysis/joint264-costs.csv').open())}
 srcrows={int(r['frame']):r for r in csv.DictReader(pin(base/'test04/cycles.csv').open())}
 ev=list(csv.reader(pin(base/'test04/joint-events.csv').open()))
 done={int(r[1]):int(r[3])/1e9 for r in ev if r[0]=='frame_done'}
 consumers={int(r[1]):list(map(int,r[2:])) for r in ev if r[0]=='consumer'}
 internal={f:[] for f in range(905,976)}
 for r in ev:
  if r[0]=='internal':internal[int(r[1])].append(list(map(int,r[2:])))
 credits=[int(r[2]) for r in ev if r[0]=='credits'];assert len(credits)==71 and max(credits)==4
 assert len(done)==len(consumers)==71 and sum(r[0]=='receipt' for r in ev)==2069
 flat={}
 for line in pin(base/'test04/blocks.txt').read_text().splitlines():
  f,tok,n,b=line.split();flat.setdefault(int(f),bytearray()).extend(bytes.fromhex(b))
 assert len(flat)==71
 for f,data in flat.items():
  old=BASE/'probes/nes-joint249/blocktest03';n=int(pin(old/f'frame{f}.meta').read_text().split()[0]);assert data==bytes.fromhex(pin(old/f'frame{f}.expected.hex').read_text())[:n]
 rows=[];batches=ranges=mapbytes=0
 fields=['BG_length','OBJ_length','map_length','CGRAM_length','OAM_length','HDMA_length','hofs','vofs','budget','mask','version','raw_count']
 context_values={name:set() for name in fields}
 for f in range(905,976):
  pp=packets(pin(BASE/f'probes/nes-joint264/arm01/frame{f}.packets'))
  assert bytes.fromhex(pin(base/f'test04/all{f}.hex').read_text())==b''.join(pp)
  controls=[p for p in pp if p[0] in (15,10,11,3)]
  assert internal[f]==[[p[0],len(p)] for p in controls]
  context=next(p for p in controls if p[0]==15)[16:40];cert=pp[0][16:]
  for i,name in enumerate(fields):context_values[name].add(int.from_bytes(context[2*i:2*i+2],'little'))
  assert int.from_bytes(context[18:20],'little')==cert[19]
  assert int.from_bytes(context[22:24],'little')==cert[20]
  dma=sum(int.from_bytes(p[14:16],'little') for p in pp if p[0]==7)
  for q in pp:
   if q[0]!=14:continue
   batches+=1;ranges+=q[20];at=21
   for _ in range(q[20]):n=q[at+2];at+=3+n;dma+=n;mapbytes+=n
   assert at==len(q)
  assert consumers[f]==[0,sum(p[0] in (2,4,5,7,8) for p in pp),dma]
  o=oldrows[f];source=int(srcrows[f]['total'])*45.454/1e6
  source_delta=round((source-float(o['source_ms']))*1e6/45.454)
  assert abs(source_delta)<=1
  poll=int(o['ARM_endpoint_poll_bytes'])*8/2625;cpu=float(o['ARM_CPI1_ms'])
  rows.append(dict(frame=f,source_ms=source,source_delta_cycles=source_delta,output_model_ms=done[f],prior264_output_ms=float(o['output_model_ms']),
   saved_vs264_ms=float(o['output_model_ms'])-done[f],saved_vs263_ms=float(o['prior263_output_ms'])-done[f],
   diagnostic_serial_ms=source+done[f],ARM_endpoint_poll_bytes=int(o['ARM_endpoint_poll_bytes']),ARM_CPI1_ms=cpu,
   serial_with_unmatched_ARM_sensitivity_ms=source+done[f]+poll+cpu,
   E1_bytes=int(o['E1_bytes']),DMA_bytes=dma,ordinary_packets=consumers[f][1],internal_packets=len(controls),
   removed_SNES_packet_reads=sum(map(len,controls)),removed_SNES_ACK_writes=13*len(controls),
   display_context_reads=24,net_removed_bus_bytes=sum(map(len,controls))+13*len(controls)-24,SNES_echo_events=0))
 assert (batches,ranges,mapbytes)==(124,2069,13406)
 summary=m['summary'];assert 'Lite Edition' in summary
 area={k:int(re.search(pattern+r'\s*:\s*([\d,]+)',summary).group(1).replace(',','')) for k,pattern in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
 report=pin(base/'map01/output_files/joint.map.rpt').read_text();hierarchy={}
 for line in report.splitlines():
  f=[v.strip() for v in line.split(';')]
  if len(f)>5 and f[1] in ['|nes_joint257:core|','|nes_output260:flow|','|nes_queue260:queue|']:
   hierarchy[f[1]]={k:int(re.match(r'\d+',v).group()) for k,v in zip(['comb','FF','RAM_bits'],f[2:5])}
 names=re.findall(r'State Machine - ([^\r\n]+)',report)
 assert any(n.endswith('nes_output260:flow|state') for n in names)
 oldarea=prior['MAP']['direct264'];delta={k:area[k]-oldarea[k] for k in area}
 result=dict(passed=True,stage='NES265',frames=71,source_bytes=sum(map(len,flat.values())),batches=batches,map_ranges=ranges,map_bytes=mapbytes,
  DMA_bytes=sum(r['DMA_bytes'] for r in rows),ordinary_packets=sum(r['ordinary_packets'] for r in rows),internal_packets=sum(r['internal_packets'] for r in rows),
  removed_SNES_packet_reads=sum(r['removed_SNES_packet_reads'] for r in rows),removed_SNES_ACK_writes=sum(r['removed_SNES_ACK_writes'] for r in rows),
  display_context_reads=24*71,net_removed_bus_bytes=sum(r['net_removed_bus_bytes'] for r in rows),SNES_echo_events=0,RTL_guards=29,max_queue_credit=4,
  MAP=dict(prior264=oldarea,replacement265=area,delta=delta,hierarchy=hierarchy,output_FSM_extracted=True),
  ARM=dict(reused264=True,changed_source=False,actual_E1_replayed_without_rebinding=True,retimed_with_RTL=False),
  display_context_fields={name:dict(observed_unique=len(values),observed_min=min(values),observed_max=max(values)) for name,values in context_values.items()},
  display_mask_raw_match_H2_frames=71,
  warm_max_output=max(rows[2:],key=lambda r:r['output_model_ms']),warm_max_serial=max(rows[2:],key=lambda r:r['diagnostic_serial_ms']),
  warm_max_serial_sensitivity=max(rows[2:],key=lambda r:r['serial_with_unmatched_ARM_sensitivity_ms']),
  warm_over_sensitivity=sum(r['serial_with_unmatched_ARM_sensitivity_ms']>1000/60 for r in rows[2:]),
  min_warm_saved_ms=min(r['saved_vs264_ms'] for r in rows[2:]),heavy=[r for r in rows if r['frame'] in (905,906,907,954,955,963,970)],
  full_path_ms=None,whole_board_margin=None,proven_whole_LE_reclaim=0,P2_selected=False,physical60fps=False,
  limitations=['native C ordinary execution; no actual general65816 or PPU display configuration application',
   '24 byte display context transport/read coverage verified, semantic binding to H2 and target register programming remain open',
   'ARM E0 refill/IRQ and tile ROM arbitration not retimed; serial sensitivity is not a bound',
   'Lite MAP partial integrated boundary, not whole FIT/STA/CDC/IO; no allocation-free display context',
   '264 single-packet active scroll prefix and aligned raw granule limitations retained'],artifact_hashes=pins)
 with (out/'costs.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('artifact_hashes','heavy')},indent=2))


if __name__=='__main__':main()
