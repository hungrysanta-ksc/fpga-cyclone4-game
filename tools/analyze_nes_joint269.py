# SPDX-License-Identifier: MIT
"""Evidence-bound STOP/bank, live polling/ROM and whole-board comparison."""
from pathlib import Path
import argparse,collections,csv,hashlib,json,re
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile
from analyze_nes_boundary269 import hierarchy
from nes_joint269 import sources


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();b=a.base.resolve();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);pins={}
 def pin(p):pins[str(p)]=sha(p);return p
 def read(p):return json.loads(pin(p).read_text(encoding='utf-8'))
 def events(q):return list(csv.reader(pin(q/'joint-events.csv').open()))
 def times(q):return {int(x[1]):int(x[3])/1e9 for x in events(q) if x[0]=='frame_done'}
 names=['cpu01','cpu-stop04','cpu-ranges01','joint02','window01','guards02','status02','board03','boundary04','rompad01']
 r={n:read(b/n/'result.json') for n in names};assert all(x['passed'] for x in r.values())
 for n in ['cpu-ranges01','cpu-stop04']:assert pin(b/n/'ordinary.sfc').read_bytes()==pin(b/'cpu01/ordinary.sfc').read_bytes()
 old=read(ROOT/'analysis/joint268-verification.json');prior={int(x['frame']):x for x in csv.DictReader(pin(ROOT/'analysis/joint268-costs.csv').open())}
 q=b/'joint02';ev=events(q);done=times(q);arm={x['frame']:x for x in r['joint02']['ARM']['frames']}
 assert sources()['nes_mux260.sv']==pin(q/'nes_mux260.sv').read_text()
 assert len(done)==71 and len(arm)==71 and sum(x[0]=='cpu267' for x in ev)==522 and sum(x[0]=='receipt' for x in ev)==2069
 assert max(int(x[2]) for x in ev if x[0]=='credits')==4
 for n in ['blocks.txt','CPU-packets.hex']:
  assert pin(q/n).read_bytes()==pin(BASE/'probes/nes-joint268/joint-reuse01'/n).read_bytes()
 for f in range(905,976):assert pin(q/f'all{f}.hex').read_bytes()==pin(BASE/f'probes/nes-joint268/joint-reuse01/all{f}.hex').read_bytes()
 for n in ['joint02','window01','guards02','status02']:
  assert pin(b/n/'nes_mux260.sv').read_bytes()==pin(q/'nes_mux260.sv').read_bytes()
 boardflow=pin(b/'board03/nes_mux260.sv').read_text().replace(' output wire tile_closed267,\n','').replace('assign tile_closed267=tiles_closed;','')
 assert boardflow==pin(q/'nes_mux260.sv').read_text()
 for n in ['nes_sink_bus165.sv','nes_sink_bridge165.sv']:assert pin(b/'status02'/n).read_bytes()==pin(b/'board03'/n).read_bytes()
 assert r['status02']['top_mux'] in pin(b/'board03/fxpak_nes_screen137_top.sv').read_text()
 for n in ['nes_core257.sv','nes_transport257.sv','nes_joint257.sv']:
  assert pin(q/n).read_bytes()==pin(BASE/'probes/nes-joint268/joint-reuse01'/n).read_bytes()
 loaded=[]
 for folder in [q,b/'window01',BASE/'probes/nes-joint268/joint-reuse01']:
  with pin(folder/'output.elf').open('rb') as f:loaded.append([(s['p_vaddr'],s['p_memsz'],s['p_flags'],hashlib.sha256(s.data()).hexdigest()) for s in ELFFile(f).iter_segments() if s['p_type']=='PT_LOAD'])
 assert loaded[0]==loaded[1]==loaded[2]
 source={int(x['frame']):x for x in csv.DictReader(pin(q/'cycles.csv').open())};rows=[];previous_wire=previous_output=0
 for f in range(905,976):
  count=collections.Counter();wire=collections.Counter()
  for x in ev:
   if x[0]=='arm267' and int(x[1])==f:count[f'{int(x[2]):02x}']+=1;wire[f'{int(x[2]):02x}']+=int(x[3])
  assert sum(wire.values())==arm[f]['SPI_bytes']
  cumulative=int(source[f]['wirebytes_cumulative']);source_wire=cumulative-previous_wire-previous_output;previous_wire=cumulative;previous_output=arm[f]['SPI_bytes']
  sm=int(source[f]['total'])*45.454/1e6;total=sm+done[f];oldtime=float(prior[f]['diagnostic_serial_ms'])
  rows.append(dict(frame=f,source_ms=sm,output_schedule_ms=done[f],diagnostic_serial_ms=total,prior268_ms=oldtime,delta_ms=total-oldtime,
   budget_gap_ms=total-1000/60,ARM_instructions=arm[f]['instructions'],SPI_bytes=arm[f]['SPI_bytes'],source_SPI_bytes=source_wire,
   shared_SPI_bytes=source_wire+arm[f]['SPI_bytes'],shared_SPI_wire_ms=(source_wire+arm[f]['SPI_bytes'])*8/2625,
   E0_polls=count['e0'],E8_polls=count['e8'],E9_batches=count['e9'],EA_retire=count['ea']))
 with (d/'costs.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 area={k:int(re.search(pattern+r'\s*:\s*([\d,]+)',r['board03']['summary']).group(1).replace(',','')) for k,pattern in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
 priorarea=old['MAP']['cleanup268'];area_delta={k:area[k]-priorarea[k] for k in area};assert not r['board03']['undriven_outputs']
 window=[];ws={int(x['frame']):x for x in csv.DictReader(pin(b/'window01/cycles.csv').open())}
 for f,t in times(b/'window01').items():
  sm=int(ws[f]['total'])*45.454/1e6;before=next(x for x in old['paired'] if x['frame']==f)
  window.append(dict(frame=f,output_ms=t,source_ms=sm,diagnostic_serial_ms=sm+t,prior268_serial_ms=before['restricted_diagnostic_serial_ms'],delta_ms=sm+t-before['restricted_diagnostic_serial_ms'],gap_ms=sm+t-1000/60))
 worst=max(rows[2:],key=lambda r:r['diagnostic_serial_ms']);h=hierarchy(b/'board03/output_files/board.map.rpt');boundary=r['boundary04']
 region=sum(h[n]['comb'] for n in ['|nes_core257:encoder|','|nes_transport257:transport|','|nes_queue260:queue|','|nes_plan_spi200:endpoint|','|nes_plan_batch206:transport|'])+h['|nes_output260:flow|']['own_comb']
 f954=next(x for x in rows if x['frame']==954);full_reads=boundary['worst954']['extra_full_status_reads'];short_bytes=f954['E0_polls']*15-24*full_reads
 result=dict(passed=True,stage='NES269',selected=names,script_sha256=sha(Path(__file__)),source_generator_sha256=sha(ROOT/'tools/nes_joint269.py'),CPU=r['cpu01'],STOP=r['cpu-stop04'],ranges=r['cpu-ranges01']['CPU'],RTL_guards=r['guards02']['guards'],status=r['status02'],ROMpad=r['rompad01'],
  MAP=dict(prior268=priorarea,current269=area,delta=area_delta,comb_deficit=area['comb']-15408,FIT=False,STA=False),
  boundary=dict(prior268=boundary,current269_region_comb=region,current269_new_region_limit=region-(area['comb']-15408),source_receipt_replacement_implemented=False,net_reclaim_proven=0),
  current269_short_status_frozen=dict(frame=954,E0_polls=f954['E0_polls'],extra_full_status_reads=full_reads,wire_saved_B=short_bytes,wire_saved_ms=short_bytes*8/2625,after_extra_8us_transfer_setup_ms=short_bytes*8/2625-full_reads*.008,extra_ARM_refill_poll_ROM_cost_ms=None,implemented=False),
  ARM_loaded_segments=loaded[0],ARM_instructions=sum(x['instructions'] for x in arm.values()),E0_polls=sum(x['E0_polls'] for x in rows),
  output_SPI_bytes=sum(x['SPI_bytes'] for x in rows),shared_SPI_bytes=sum(x['shared_SPI_bytes'] for x in rows),warm_max=worst,warm_over=sum(x['budget_gap_ms']>0 for x in rows[2:]),
  restricted_ROM=window,full_path_ms=None,P2_selected=False,physical60fps=False,
  limitations=['65816 STOP tests use a bus-status model; separate RTL tests check the matching contract, not live CPU/FPGA co-simulation.',
   'Actual ARM serializer/refill and IRQ bodies at service boundaries; CPI1 is not hardware cycles, full RUN/NVIC/input planner absent.',
   'Forced-blank ordinary65816 trace; active VBlank/map/tile/final display CPU and full program link remain open.',
   'ROM contention uses real cache/arbiter/reader with synthetic core requests; no universal worst-case/physical bound.',
   'Local STOP/read/ACK ownership and whole MAP are tested; whole-board functional/CDC/IO/STA and every external WRAM writer are not qualified.',
   'Broader6494comb region and compact status savings are accounting/design candidates; no new source/receipt replacement or gain claimed.'],pins=pins)
 (d/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(warm_max=worst,warm_over=result['warm_over'],MAP=result['MAP'],restricted_ROM=window)))


if __name__=='__main__':main()
