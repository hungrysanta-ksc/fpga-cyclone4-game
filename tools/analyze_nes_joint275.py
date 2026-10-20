# SPDX-License-Identifier: MIT
"""Same-frame live inline costs, descriptor identity and whole Lite replacement."""
from pathlib import Path
import argparse,collections,csv,json,re
from nes_delta231 import BASE,ROOT,sha
from nes_inline275 import unwrap,source
from probe_nes_joint264 import packets
from probe_nes_primitive273 import events as decode,oracle
from probe_nes_arm264 import u16

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',type=Path,required=True)
 ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();b=a.base.resolve();d=a.out.resolve()
 assert not d.exists();d.mkdir(parents=True);pins={}
 def pin(p):pins[str(p)]=sha(p);return p
 def read(p):return json.loads(pin(p).read_text(encoding='utf-8'))
 def rows(p):return list(csv.DictReader(pin(p).open()))
 def events(p):return list(csv.reader(pin(p/'joint-events.csv').open()))
 def done(ev):return {int(x[1]):int(x[3])/1e9 for x in ev if x[0]=='frame_done'}
 selected=['arm02','armguards01','test04','window01','guards02','spiguards01','board01']
 results={n:read(b/n/'result.json') for n in selected};assert all(x['passed'] for x in results.values())
 reuse=[]
 for p in (b/'guards01').iterdir():
  if p.is_file() and p.suffix in ('.sv','.c','.hex','.lens','.desc','.cfg','.expected','.palette','.records') and p.name not in ('all905.hex','all905.lens'):
   assert sha(pin(p))==sha(pin(b/'guards02'/p.name));reuse.append(p.name)
 for i in results['guards02']['reused_exact_evidence']:
  assert pin(b/f'guards01/guard{i}.log').read_bytes()==pin(b/f'guards02/guard{i}.log').read_bytes()
 assert len(results['guards02']['guards'])==19
 prior=BASE/'probes/nes-joint274';q=b/'test04'
 old={int(x['frame']):x for x in rows(prior/'analysis01/costs.csv')}
 prior_summary=read(prior/'analysis01/result.json')
 ref=read(BASE/'probes/nes-joint270/test05/result.json')
 changed=[n for n,h in results['test04']['rtl_hashes'].items() if ref['rtl_hashes'].get(n)!=h]
 assert changed==['nes_queue260.sv','nes_mux260.sv'] or set(changed)=={'nes_queue260.sv','nes_mux260.sv'}
 for n,h in results['test04']['rtl_hashes'].items():
  assert sha(pin(q/n))==h==sha(pin(b/'window01'/n))
 for n in changed:
  assert sha(pin(q/n))==sha(pin(b/'guards02'/n))
  board=pin(b/'board01'/n).read_text()
  if n=='nes_mux260.sv':
   def logical_flow(s):
    assert s.count(' output wire tile_closed267,\n')==1
    assert s.count('assign tile_closed267=tiles_closed;')==1
    return s.replace(' output wire tile_closed267,\n','').replace('assign tile_closed267=tiles_closed;','')
   assert logical_flow(board)==(q/n).read_text()
   assert logical_flow(pin(BASE/'probes/nes-joint270/board02'/n).read_text())==\
    pin(BASE/'probes/nes-joint270/test05'/n).read_text()
  else:assert board==(q/n).read_text()
 for n in ['blocks.txt','commands.hex','stream.hex','expected.hex','hashes.hex','certs.hex']:
  assert pin(q/n).read_bytes()==pin(prior/'test01'/n).read_bytes(),n
 assert sum(int(x.split()[2]) for x in (q/'blocks.txt').read_text().splitlines())==83240
 for name in ['arm02','test04','window01']:
  assert pin(b/name/'nes_output264.c').read_text()==source()
 for name in ['CPU-bus.csv','CPU-ordinary.sfc','CPU-packets.hex']:
  assert pin(q/name).read_bytes()==pin(prior/'test01'/name).read_bytes()
 ev=events(q);times=done(ev);arm={x['frame']:x for x in results['test04']['ARM']['frames']}
 assert len(times)==71 and sum(x[0]=='cpu267' for x in ev)==544
 assert sum(x[0]=='receipt' for x in ev)==2069
 assert max(int(x[2]) for x in ev if x[0]=='credits')==4
 sc={int(x['frame']):x for x in rows(q/'cycles.csv')}
 out=[];program_bytes=wrapped=0
 for f in range(905,976):
  physical=packets(pin(b/f'arm02/frame{f}.packets'))
  logical=[];pb=extra=0
  for p in physical:
   legacy,program=unwrap(p);logical.append(legacy)
   if program:pb+=len(program);extra+=len(program)+2;wrapped+=1
  expected=packets(pin(prior/f'arm01/frame{f}.packets'))
  assert logical==expected
  for p in physical:
   legacy,program=unwrap(p)
   assert decode(program,2,legacy)==oracle(legacy,u16(logical[0],30),logical[0][36])
  actual=[bytes.fromhex(x['tx'])[1:-2] for x in read(q/f'arm{f}.json')['transfers'] if x['tx'].startswith('e1')]
  assert actual==physical
  assert extra==int(old[f]['future_inline_extra_wire'])
  ct=collections.Counter();wire=collections.Counter();instructions=0
  for x in ev:
   if x[0]=='arm267' and int(x[1])==f:
    ct[int(x[2])]+=1;wire[int(x[2])]+=int(x[3]);instructions+=int(x[5])
  assert wire[225]==sum(len(p)+3 for p in physical)
  assert sum(wire.values())==arm[f]['SPI_bytes']
  sm=int(sc[f]['total'])*45.454/1e6;total=sm+times[f]
  previous_transactions=sum(int(old[f][k]) for k in
   ['packets','E0_full','E2_short','E8_polls','E9_batches','EA_retire'])
  transport_instruction_delta=(sum(wire.values())-int(old[f]['SPI_bytes']))*8/2625+\
   (instructions-int(old[f]['ARM_IRQ_event_instructions']))/84000+\
   (sum(ct.values())-previous_transactions)*0.008
  out.append(dict(frame=f,source_ms=sm,output_schedule_ms=times[f],diagnostic_serial_ms=total,
   prior274_ms=float(old[f]['diagnostic_serial_ms']),delta274_ms=total-float(old[f]['diagnostic_serial_ms']),
   prior270_ms=float(old[f]['prior270_ms']),budget_gap_ms=total-1000/60,
   E1_wire=wire[225],reference_wire_extra=extra,program_bytes=pb,
   E0_full=ct[224],E2_short=ct[226],status_polls=ct[224]+ct[226],
   prior274_E2=int(old[f]['E2_short']),SPI_bytes=sum(wire.values()),
   prior274_SPI_bytes=int(old[f]['SPI_bytes']),ARM_instructions=arm[f]['instructions'],
   ARM_IRQ_event_instructions=instructions,
   prior274_ARM_IRQ_event_instructions=int(old[f]['ARM_IRQ_event_instructions']),
   transaction_delta=sum(ct.values())-previous_transactions,
   wire_instruction_transaction_delta_ms=transport_instruction_delta,
   remaining_schedule_delta_ms=total-float(old[f]['diagnostic_serial_ms'])-transport_instruction_delta,
   E8=ct[232],E9=ct[233],EA=ct[234]))
  program_bytes+=pb
 with (d/'costs.csv').open('w',newline='') as h:
  w=csv.DictWriter(h,fieldnames=list(out[0]),lineterminator='\n');w.writeheader();w.writerows(out)
 we=events(b/'window01');oe=events(prior/'window01')
 ws={int(x['frame']):x for x in rows(b/'window01/cycles.csv')};window=[]
 oldwindow={x['frame']:x for x in prior_summary['restricted_ROM']}
 for f,t in done(we).items():
  sm=int(ws[f]['total'])*45.454/1e6
  oldtotal=oldwindow[f]['diagnostic_serial_ms']
  def cost(ev):
   lines=[x for x in ev if x[0]=='arm267' and int(x[1])==f]
   return dict(E2=sum(int(x[2])==226 for x in lines),SPI=sum(int(x[3]) for x in lines),
               ARM_IRQ_event_instructions=sum(int(x[5]) for x in lines))
  window.append(dict(frame=f,diagnostic_serial_ms=sm+t,prior274_ms=oldtotal,
   delta274_ms=sm+t-oldtotal,budget_gap_ms=sm+t-1000/60,current=cost(we),prior=cost(oe)))
 def end(ev):return max(int(x[2]) for x in ev if x[0]=='frame_done')/1e9
 sequence=dict(current_end_ms=end(we),prior274_end_ms=end(oe),delta_ms=end(we)-end(oe),
  note='Absolute three-frame completion includes shifted ROM/poll wait; individual907 delta is not an independent gain.')
 def mapping(folder):
  s=pin(folder/'output_files/board.map.summary').read_text()
  values={}
  for key,label in [('LE','Total logic elements'),('comb','Total combinational functions'),
                    ('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]:
   values[key]=int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',s).group(1).replace(',',''))
  rpt=pin(folder/'output_files/board.map.rpt').read_text()
  ent={};own={}
  for line in rpt.splitlines():
   fields=[v.strip() for v in line.split(';')]
   if len(fields)==14 and re.fullmatch(r'\d+ \(\d+\)',fields[2]):
    own[fields[10]]={k:int(re.search(r'\((\d+)\)',fields[i]).group(1)) for k,i in [('comb',2),('FF',3)]}
    if fields[-3] in ['nes_output260','nes_queue260','nes_core257']:
     ent[fields[-3]]=dict(comb=fields[2],FF=fields[3],RAM_bits=fields[4])
  assert {k:sum(v[k] for v in own.values()) for k in ['comb','FF']}=={k:values[k] for k in ['comb','FF']}
  return values,ent,own
 m,entities,own=mapping(b/'board01');oldmap,oldentities,oldown=mapping(BASE/'probes/nes-joint270/board02')
 own_changes=[]
 for key in sorted(own.keys()|oldown.keys()):
  before=oldown.get(key,dict(comb=0,FF=0));after=own.get(key,dict(comb=0,FF=0))
  if before!=after:own_changes.append(dict(path=key,before=before,after=after,delta={k:after[k]-before[k] for k in before}))
 assert sum(x['delta']['comb'] for x in own_changes)==450
 assert m==dict(LE=22898,comb=18130,FF=8877,RAM_bits=303712)
 assert oldmap['comb']==17680
 warm=[x for x in out if x['frame']>=907];worst=max(warm,key=lambda x:x['diagnostic_serial_ms'])
 r=dict(passed=True,stage=275,scope=__doc__,selected=selected,frames=71,
  reference_program_transmitted=True,reference_program_executed_by_FPGA=True,
  changed_RTL=changed,packets=1231,wrapped_packets=wrapped,program_bytes=program_bytes,
  board_binding='Flow adds only the same tile_closed267 output/assign already present in270 board vs simulation; exact normalization checked for both versions. Queue byte-identical.',
  source_bytes=83240,map_ranges=2069,map_bytes=13406,map_tile_DMA_bytes=26350,
  metadata_per_frame=8570,receipt_per_frame=754,CRC_per_frame=64,ordinary_CPU_trace_commands=544,
  max_credit=4,warm_max=worst,warm_over=sum(x['diagnostic_serial_ms']>1000/60 for x in warm),
  over_frames=[x['frame'] for x in warm if x['diagnostic_serial_ms']>1000/60],
  new_over_frames=[x['frame'] for x in warm if x['diagnostic_serial_ms']>1000/60>=x['prior274_ms']],
  SPI=dict(total=sum(x['SPI_bytes'] for x in out),prior274_total=sum(x['prior274_SPI_bytes'] for x in out),
   extra_E1_wire=sum(x['reference_wire_extra'] for x in out),
   E0=sum(x['E0_full'] for x in out),E2=sum(x['E2_short'] for x in out),
   prior274_E2=sum(x['prior274_E2'] for x in out)),
  frame954=next(x for x in out if x['frame']==954),restricted_ROM=window,restricted_sequence=sequence,
  MAP=dict(current=m,prior270=oldmap,delta={k:m[k]-oldmap[k] for k in m},entities=entities,
   prior_entities=oldentities,own_changes=own_changes,
   changed_queue_flow_own_delta=484,other_synthesis_optimization_delta=-34,
   comb_deficit=m['comb']-15408,prior_deficit=2272,FIT=False,STA=False),
  ARM=dict(standalone=(b/'arm02/size.log').read_text(),full=(q/'size-rom.log').read_text(),
   standalone_stack=results['arm02']['stack_observed'],live_stack=results['test04']['ARM']['stack_observed'],
   IRQ_bodies=len(results['test04']['ARM']['IRQ_cases'])),
  guards=results['guards02']['guards'],SPI_guards=results['spiguards01']['log'],
  reused_guard_input_source_files=reuse,
  ARM_wrap=results['armguards01']['counter_wrap'],
  full_path_ms=None,single_source_receipt_parser_FSM=False,P2_selected=False,
  physical=False,full_RUN=False,actual_SNES_live=False,
  decision='Reject inline references as a time/area optimization. Keep the verified descriptor/STOP contract as evidence; source/query/core replacement remains incomplete.',
  input_hashes=pins,script_sha256=sha(Path(__file__)))
 (d/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({k:r[k] for k in ('passed','warm_max','restricted_ROM','restricted_sequence','MAP','ARM')},indent=2))

if __name__=='__main__':main()
