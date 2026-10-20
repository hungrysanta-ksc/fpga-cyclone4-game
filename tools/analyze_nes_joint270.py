# SPDX-License-Identifier: MIT
"""Reconcile actual short/full polls, ROM contention and whole-board costs."""
from pathlib import Path
import argparse,collections,csv,hashlib,json,re
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_boundary269 import hierarchy
from probe_nes_arm264 import ELFFile

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--spi',default='spiguards01');p.add_argument('--guards',default='guards01');p.add_argument('--window',default='window01');a=p.parse_args()
 b=a.base.resolve();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);pins={}
 def pin(p):pins[str(p)]=sha(p);return p
 def read(p):return json.loads(pin(p).read_text(encoding='utf-8'))
 def events(q):return list(csv.reader(pin(q/'joint-events.csv').open()))
 def done(q):return {int(x[1]):int(x[3])/1e9 for x in events(q) if x[0]=='frame_done'}
 names=['test05',a.window,a.guards,a.spi,'armguards02','board02'];r={n:read(b/n/'result.json') for n in names};assert all(x['passed'] for x in r.values())
 assert r[a.guards]['guards']==list(range(1,39)) and len(r['armguards02']['short_status_guards'])==6
 q=b/'test05';old=read(ROOT/'analysis/joint269-verification.json');prev={int(x['frame']):x for x in csv.DictReader(pin(ROOT/'analysis/joint269-costs.csv').open())}
 assert sha(pin(q/'joint266_tb.sv'))==r['test05']['tb_sha256']
 ev=events(q);times=done(q);arm={x['frame']:x for x in r['test05']['ARM']['frames']};assert len(times)==len(arm)==71
 assert sum(x[0]=='cpu267' for x in ev)==522 and sum(x[0]=='receipt' for x in ev)==2069 and max(int(x[2]) for x in ev if x[0]=='credits')==4
 prior=BASE/'probes/nes-joint269/joint02'
 for n in ['blocks.txt','CPU-packets.hex','CPU-bus.csv','CPU-ordinary.sfc','nes_core257.sv','nes_plan_batch206.sv']:
  assert pin(q/n).read_bytes()==pin(prior/n).read_bytes(),n
 for f in range(905,976):assert pin(q/f'all{f}.hex').read_bytes()==pin(prior/f'all{f}.hex').read_bytes()
 shared=['nes_spi270.sv','nes_queue260.sv','nes_transport257.sv','nes_plan_spi200.sv']
 for n in shared:
  for folder in [b/a.window,b/a.spi,b/'board02']:assert pin(q/n).read_bytes()==pin(folder/n).read_bytes(),(folder,n)
 for n in shared[:3]:assert pin(q/n).read_bytes()==pin(b/a.guards/n).read_bytes()
 # Actual final C, unchanged SNES STOP and source/receipt/plan RAM operations.
 assert pin(q/'nes_output264.c').read_bytes()==pin(ROOT/'tools/nes_output270.c').read_bytes()
 assert pin(q/'nes_spi270.sv').read_bytes()==pin(ROOT/'tools/nes_spi270.sv').read_bytes()
 transport=pin(q/'nes_transport257.sv').read_text();before=pin(prior/'nes_transport257.sv').read_text()
 def source_body(s):
  s=s[s.index(' (* ramstyle='):s.index(' reg read_bank')]
  return re.sub(r' function automatic \[7:0\] c8\([^\n]+\n.*? endfunction\n','',s,flags=re.S)
 assert source_body(transport)==source_body(before)
 with pin(q/'output.elf').open('rb') as f:segments=[(s['p_vaddr'],s['p_memsz'],s['p_flags'],hashlib.sha256(s.data()).hexdigest()) for s in ELFFile(f).iter_segments() if s['p_type']=='PT_LOAD']
 for folder in [b/a.window]:
  with pin(folder/'output.elf').open('rb') as f:assert segments==[(s['p_vaddr'],s['p_memsz'],s['p_flags'],hashlib.sha256(s.data()).hexdigest()) for s in ELFFile(f).iter_segments() if s['p_type']=='PT_LOAD']
 assert r['armguards02']['ELF_sha256']==sha(q/'output.elf')
 source={int(x['frame']):x for x in csv.DictReader(pin(q/'cycles.csv').open())};oldsource={int(x['frame']):x for x in csv.DictReader(pin(prior/'cycles.csv').open())}
 rows=[];previous_wire=previous_output=0
 for f in range(905,976):
  count=collections.Counter();wire=collections.Counter()
  for x in ev:
   if x[0]=='arm267' and int(x[1])==f:count[f'{int(x[2]):02x}']+=1;wire[f'{int(x[2]):02x}']+=int(x[3])
  assert sum(wire.values())==arm[f]['SPI_bytes']
  # Identical source bytes/RTL do not imply identical ACK clock alignment.
  # Carry the measured source total rather than freezing the269 timing.
  source_delta=int(source[f]['total'])-int(oldsource[f]['total'])
  cumulative=int(source[f]['wirebytes_cumulative']);source_wire=cumulative-previous_wire-previous_output;previous_wire=cumulative;previous_output=arm[f]['SPI_bytes']
  sm=int(source[f]['total'])*45.454/1e6;total=sm+times[f];oldtime=float(prev[f]['diagnostic_serial_ms'])
  rows.append(dict(frame=f,source_ms=sm,source_delta_cycles=source_delta,output_schedule_ms=times[f],diagnostic_serial_ms=total,prior269_ms=oldtime,delta_ms=total-oldtime,budget_gap_ms=total-1000/60,
   ARM_instructions=arm[f]['instructions'],SPI_bytes=arm[f]['SPI_bytes'],source_SPI_bytes=source_wire,shared_SPI_bytes=source_wire+arm[f]['SPI_bytes'],shared_SPI_wire_ms=(source_wire+arm[f]['SPI_bytes'])*8/2625,
   E0_full=count['e0'],E2_short=count['e2'],status_polls=count['e0']+count['e2'],prior269_E0=int(prev[f]['E0_polls']),status_wire_bytes=wire['e0']+wire['e2'],
   status_wire_ms=(wire['e0']+wire['e2'])*8/2625,status_transfer_setup_ms=(count['e0']+count['e2'])*.008,
   status_setup_delta_ms=(count['e0']+count['e2']-int(prev[f]['E0_polls']))*.008,
   foreground_CPI1_delta_ms=(arm[f]['instructions']-int(prev[f]['ARM_instructions']))/84000,
   E8_polls=count['e8'],E9_batches=count['e9'],EA_retire=count['ea']))
 with (d/'costs.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 area={k:int(re.search(pat+r'\s*:\s*([\d,]+)',r['board02']['summary']).group(1).replace(',','')) for k,pat in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
 priorarea=old['MAP']['current269'];delta={k:area[k]-priorarea[k] for k in area};assert not r['board02']['undriven_outputs']
 h=hierarchy(pin(b/'board02/output_files/board.map.rpt'));region={n:h[n]['comb'] for n in ['|nes_core257:encoder|','|nes_transport257:transport|','|nes_queue260:queue|','|nes_plan_spi200:endpoint|','|nes_plan_batch206:transport|','|nes_spi270:spi_front270|']};region['output exclusive']=h['|nes_output260:flow|']['own_comb']
 window=[];ws={int(x['frame']):x for x in csv.DictReader(pin(b/a.window/'cycles.csv').open())}
 prior_window=BASE/'probes/nes-joint269/window01'
 we=events(b/a.window);pe=events(prior_window)
 wa={x['frame']:x for x in r[a.window]['ARM']['frames']}
 pa={x['frame']:x for x in read(prior_window/'result.json')['ARM']['frames']}
 def polls(ev,f):
  c=collections.Counter();w=collections.Counter()
  for x in ev:
   if x[0]=='arm267' and int(x[1])==f:c[int(x[2])]+=1;w[int(x[2])]+=int(x[3])
  return dict(E0=c[224],E2=c[226],polls=c[224]+c[226],status_bytes=w[224]+w[226],SPI_bytes=sum(w.values()))
 for f,t in done(b/a.window).items():
  sm=int(ws[f]['total'])*45.454/1e6;priorrow=next(x for x in old['restricted_ROM'] if x['frame']==f)
  cp,pp=polls(we,f),polls(pe,f)
  window.append(dict(frame=f,source_ms=sm,output_ms=t,diagnostic_serial_ms=sm+t,prior269_ms=priorrow['diagnostic_serial_ms'],delta_ms=sm+t-priorrow['diagnostic_serial_ms'],budget_gap_ms=sm+t-1000/60,
   current_polls=cp,prior_polls=pp,status_wire_delta_ms=(cp['status_bytes']-pp['status_bytes'])*8/2625,
   status_setup_delta_ms=(cp['polls']-pp['polls'])*.008,foreground_CPI1_delta_ms=(wa[f]['instructions']-pa[f]['instructions'])/84000))
 worst=max(rows[2:],key=lambda x:x['diagnostic_serial_ms']);f954=next(x for x in rows if x['frame']==954)
 result=dict(passed=True,stage='NES270',selected=names,script_sha256=sha(Path(__file__)),
  scope='Common host SPI sampler/counter/snapshot/CRC8 replaces source/output/plan endpoint duplicates; source/receipt core and CRC16 unchanged.',
  MAP=dict(prior269=priorarea,current270=area,delta=delta,comb_deficit=area['comb']-15408,FIT=False,STA=False),
  replacement=dict(current_region=region,region_comb=sum(region.values()),new_region_limit=sum(region.values())-(area['comb']-15408),whole_comb_reclaim=-delta['comb'],receipt_core_replaced=False,extra_RAM_bits=delta['RAM_bits']),
  frames=71,source_bytes=83240,map_ranges=2069,CPU_commands=522,max_credit=4,CPU269_unchanged=True,
  source_timing_changes=[dict(frame=x['frame'],delta_cycles=x['source_delta_cycles']) for x in rows if x['source_delta_cycles']],
  ARM_loaded_segments=segments,ARM_size=pin(q/'size-rom.log').read_text(),ARM_observed_stack=r['test05']['ARM']['stack_observed'],ARM_instructions=sum(x['instructions'] for x in arm.values()),IRQ_bodies=len(r['test05']['ARM']['IRQ_cases']),
  E0_full=sum(x['E0_full'] for x in rows),E2_short=sum(x['E2_short'] for x in rows),status_polls=sum(x['status_polls'] for x in rows),output_SPI_bytes=sum(x['SPI_bytes'] for x in rows),shared_SPI_bytes=sum(x['shared_SPI_bytes'] for x in rows),
  warm_max=worst,warm_over=sum(x['budget_gap_ms']>0 for x in rows[2:]),
  warm_delta_ms=dict(minimum=min(x['delta_ms'] for x in rows[2:]),maximum=max(x['delta_ms'] for x in rows[2:]),regressed_frames=[x['frame'] for x in rows[2:] if x['delta_ms']>0]),
  frame954=f954,restricted_ROM=window,arm_guards=r['armguards02'],SPI_guards=r[a.spi],RTL_guards=r[a.guards]['guards'],
  full_path_ms=None,P2_selected=False,physical60fps=False,
  candidate_decision='Conditional experiment only: normal warm timing improves, restricted warm907 regresses; whole-board comb still exceeds capacity.',
  limitations=['CPI1 and IRQ bodies at service boundaries are not full RUN/NVIC/hardware cycles.',
   'Forced-blank actual26965816 ordinary bus trace; map/tile/final display remain modeled. No new full CPU/FPGA STOP co-simulation.',
   'ROM cache/arbiter/reader RTL uses synthetic competing core requests; three restricted frames are not a worst-case bound.',
   'Common reset requires SPI bus quiescence; local fault/STOP, CRC and stale ACK are guarded. Board-level reset/CDC/IO/STA are not qualified.',
   'Core source/receipt control is retained; host SPI reclamation alone does not establish fit or mapper margin.'],pins=pins)
 (d/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({k:result[k] for k in ['warm_max','warm_over','MAP','replacement','E0_full','E2_short','restricted_ROM']}))

if __name__=='__main__':main()
