# SPDX-License-Identifier: MIT
"""Hash-bound H2/phase-RAM area and time comparison; CPU timeline stays separate."""
import argparse,csv,hashlib,json,re
from collections import Counter
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_joint266 import sources


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--cpu',action='append',required=True);a=p.parse_args()
 out=a.out.resolve();assert not out.exists();out.mkdir(parents=True);base=BASE/'probes/nes-joint266';pins={}
 def pin(path):pins[path.relative_to(BASE).as_posix()]=sha(path);return path
 def read(path):return json.loads(pin(path).read_text(encoding='utf-8'))
 results={name:read(base/name/'result.json') for name in ['test02','test03','guards01','map01',*a.cpu]}
 assert results['test03']['frames']==71 and results['guards01']['guards']==list(range(1,39))
 for name,res in results.items():
  assert res['passed']
  for n,h in res['rtl_hashes'].items():assert sha(pin(base/name/n))==h,(name,n)
  for n,s in sources().items():assert hashlib.sha256(s.encode()).hexdigest()==res['rtl_hashes'][n],(name,n)
  for path,h in res.get('input_hashes',{}).items():assert sha(pin(BASE/path))==h,(name,path)
  for path in (base/name).glob('*.log'):pin(path)
 assert results['map01']['test_sha256']==sha(base/'test02/result.json')
 for i in range(1,39):assert f'PASS DIRECT266 GNEG={i}' in (base/'guards01'/f'guard{i}.log').read_text()
 for path,h in results['test03']['input_hashes'].items():assert sha(pin(BASE/path))==h,path
 old=read(ROOT/'analysis/joint265-verification.json')
 oldrows={int(r['frame']):r for r in csv.DictReader(pin(ROOT/'analysis/joint265-costs.csv').open())}
 srcrows={int(r['frame']):r for r in csv.DictReader(pin(base/'test03/cycles.csv').open())}
 ev=list(csv.reader(pin(base/'test03/joint-events.csv').open()))
 done={int(r[1]):int(r[3])/1e9 for r in ev if r[0]=='frame_done'}
 consumers={int(r[1]):list(map(int,r[2:])) for r in ev if r[0]=='consumer'}
 credits=[int(r[2]) for r in ev if r[0]=='credits'];assert len(credits)==71 and max(credits)==4
 assert len(done)==len(consumers)==71 and sum(r[0]=='receipt' for r in ev)==2069
 display={int(r[1]):list(map(int,r[2:])) for r in ev if r[0]=='display266'};assert len(display)==71
 assert display[975][0]==12*71
 assert pin(base/'test03/blocks.txt').read_bytes()==pin(BASE/'probes/nes-joint265/test04/blocks.txt').read_bytes()
 rows=[];prevpoll=0
 for f in range(905,976):
  o=oldrows[f];source=int(srcrows[f]['total'])*45.454/1e6;polls=display[f][1]-prevpoll;prevpoll=display[f][1]
  assert consumers[f]==[0,int(o['ordinary_packets']),int(o['DMA_bytes'])]
  assert pin(base/f'test03/all{f}.hex').read_bytes()==pin(BASE/f'probes/nes-joint265/test04/all{f}.hex').read_bytes()
  rows.append(dict(frame=f,source_ms=source,source_delta_cycles=round((source-float(o['source_ms']))*1e6/45.454),
   output_model_ms=done[f],prior265_output_ms=float(o['output_model_ms']),prior264_output_ms=float(o['prior264_output_ms']),
   delta_vs265_us=(done[f]-float(o['output_model_ms']))*1000,saved_vs264_ms=float(o['prior264_output_ms'])-done[f],
   diagnostic_serial_ms=source+done[f],serial_with_unmatched_ARM_sensitivity_ms=source+done[f]+int(o['ARM_endpoint_poll_bytes'])*8/2625+float(o['ARM_CPI1_ms']),
   display_reads=12,display_ready_polls=polls,ordinary_packets=int(o['ordinary_packets']),DMA_bytes=int(o['DMA_bytes']),SNES_echo_events=0))
 summary=results['map01']['summary'];assert 'Lite Edition' in summary
 area={k:int(re.search(pattern+r'\s*:\s*([\d,]+)',summary).group(1).replace(',','')) for k,pattern in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
 report=pin(base/'map01/output_files/joint.map.rpt').read_text();hierarchy={}
 for line in report.splitlines():
  f=[v.strip() for v in line.split(';')]
  if len(f)>5 and f[1] in ['|nes_joint257:core|','|nes_output260:flow|','|nes_queue260:queue|']:
   hierarchy[f[1]]={k:int(re.match(r'\d+',v).group()) for k,v in zip(['comb','FF','RAM_bits'],f[2:5])}
 names=re.findall(r'State Machine - ([^\r\n]+)',report)
 assert any(n.endswith('nes_output260:flow|state') for n in names) and any(n.endswith('nes_core257:encoder|state') for n in names)
 priorarea=old['MAP']['replacement265'];cpu=[]
 warnings={stage:dict(Counter(re.findall(r'Warning \((\d+)\)',pin(BASE/f'probes/nes-joint{stage}/map01/map.log').read_text()))) for stage in ['265','266']}
 assert warnings['265']==warnings['266']
 for name in a.cpu:
  c=results[name]['cpu'];assert c['passed'] and c['display_reads']==12 and 225<=c['ack_scanline']<=261 and all(c['HDMA_reads'])
  for file in ['display.sfc','capture.lua','cpu-bus.csv','ppu.csv','rpc.do','joint266_tb.sv','expected-display.hex']:pin(base/name/file)
  assert sha(base/name/'display.sfc')==results[name]['rom_sha256']
  c.update(read_span_master=c['last_read_master']-c['first_read_master'],VBlank_wait_master=c['program_start_master']-c['last_read_master'],program_to_ACK_master=c['final_ack_master']-c['program_start_master'],rom_body_bytes=results[name]['rom_body_bytes'])
  cpu.append(c)
 assert sorted(c['frame'] for c in cpu)==[905,906,907] and [c['bank'] for c in sorted(cpu,key=lambda c:c['frame'])]==[0,1,0]
 r=dict(passed=True,stage='NES266',frames=71,source_bytes=old['source_bytes'],batches=124,map_ranges=2069,map_bytes=13406,DMA_bytes=sum(r['DMA_bytes'] for r in rows),
  ordinary_packets=sum(r['ordinary_packets'] for r in rows),internal_packets=old['internal_packets'],SNES_echo_events=0,RTL_guards=38,max_queue_credit=4,
  display_view_bytes=12,phase_RAM_offsets=[864,867],H2_RAM=[832,863],new_RAM_bits=0,display_polls=sum(r['display_ready_polls'] for r in rows),
  MAP=dict(prior265=priorarea,replacement266=area,delta={k:area[k]-priorarea[k] for k in area},hierarchy=hierarchy,output_and_core_FSM_extracted=True,warning_counts=warnings),
  actual65816_display=cpu,ARM=dict(reused264=True,retimed_with_RTL=False),
  warm_max_output=max(rows[2:],key=lambda r:r['output_model_ms']),warm_max_serial=max(rows[2:],key=lambda r:r['diagnostic_serial_ms']),
  warm_max_serial_sensitivity=max(rows[2:],key=lambda r:r['serial_with_unmatched_ARM_sensitivity_ms']),
  warm_over_sensitivity=sum(r['serial_with_unmatched_ARM_sensitivity_ms']>1000/60 for r in rows[2:]),
  min_warm_saved_vs264_ms=min(r['saved_vs264_ms'] for r in rows[2:]),max_added_vs265_us=max(r['delta_vs265_us'] for r in rows),
  heavy=[r for r in rows if r['frame'] in (905,906,907,954,955,963,970)],
  full_path_ms=None,whole_board_margin=None,proven_whole_LE_reclaim=0,P2_selected=False,physical60fps=False,
  limitations=['actual65816 display/HDMA/ACK only; ordinary and map transfers remain native C/bus model',
   'HDMA WRAM fixture preload from independently verified metadata; no full rendered-frame pixel oracle',
   'file RPC stretches RTL time; CPU/VBlank clocks are separate observations, not a full-frame bound',
   'ARM E0 refill/IRQ and actual tile ROM arbitration not retimed; prior sensitivity is unmatched',
   'Lite MAP partial integrated boundary, not whole FIT/STA/CDC/IO or recovery of whole240 deficit',
   'recorded display cases mask18/raw2; raw0/mask1e branches are not new actual65816 evidence',
   '264 single-packet active scroll prefix and aligned raw granule limitations retained'],artifact_hashes=pins)
 with (out/'costs.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({k:v for k,v in r.items() if k not in ('artifact_hashes','heavy')},indent=2))


if __name__=='__main__':main()
