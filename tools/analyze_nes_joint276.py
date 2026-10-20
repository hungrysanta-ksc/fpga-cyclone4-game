# SPDX-License-Identifier: MIT
"""Bind original wire, unified core, full diagnostic schedule and whole MAP."""
from pathlib import Path
import argparse,collections,csv,difflib,json,re,sys
from nes_delta231 import BASE,ROOT,sha
from probe_nes_joint264 import packets
sys.path.insert(0,str(BASE/'.tools/arm259-python'))
from elftools.elf.elffile import ELFFile

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',type=Path,required=True)
 ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();b=a.base.resolve();d=a.out.resolve()
 assert not d.exists();d.mkdir(parents=True);pins={}
 def pin(p):pins[str(p)]=sha(p);return p
 def read(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
 def rows(p):return list(csv.DictReader(pin(p).open()))
 def events(p):return list(csv.reader(pin(p/'joint-events.csv').open()))
 def done(ev):return {int(x[1]):int(x[3])/1e9 for x in ev if x[0]=='frame_done'}
 selected=['test03','window01','guards01','board01']
 results={n:read(b/n/'result.json') for n in selected};assert all(x['passed'] for x in results.values())
 prior=BASE/'probes/nes-joint274';prev=BASE/'probes/nes-joint275';q=b/'test03'
 p274=read(prior/'analysis01/result.json');p275=read(prev/'analysis01/result.json')
 old={int(x['frame']):x for x in rows(prior/'analysis01/costs.csv')}
 inline={int(x['frame']):x for x in rows(prev/'analysis01/costs.csv')}
 oldrtl=read(prior/'test01/result.json')['rtl_hashes']
 changed=[n for n,h in results['test03']['rtl_hashes'].items() if oldrtl.get(n)!=h]
 assert set(changed)=={'nes_core257.sv','nes_joint257.sv','nes_queue260.sv','nes_mux260.sv','nes_joint266.sv'}
 for n,h in results['test03']['rtl_hashes'].items():
  assert sha(pin(q/n))==h==sha(pin(b/'window01'/n))
  if n in results['guards01']['rtl_hashes']:assert sha(pin(b/'guards01'/n))==h
 # Normalize only pre-existing board wiring; compare exact differences on
 # both old and new boundaries, never accept an arbitrary normalized hash.
 board_diffs={}
 for n in changed:
  bd=pin(b/'board01'/n).read_text();sim=(q/n).read_text()
  oldbd=pin(BASE/'probes/nes-joint270/board02'/n).read_text()
  oldsim=pin(prior/'test01'/n).read_text()
  def delta(x,y):
   return [v for v in difflib.unified_diff(x.splitlines(),y.splitlines(),n=0)
           if v.startswith(('+','-')) and not v.startswith(('+++','---'))]
  assert delta(sim,bd)==delta(oldsim,oldbd),n
  board_diffs[n]=delta(sim,bd)
  (d/(n+'.board.diff')).write_text('\n'.join(difflib.unified_diff(sim.splitlines(),bd.splitlines()))+'\n')
 for n in ['blocks.txt','commands.hex','stream.hex','expected.hex','hashes.hex','certs.hex',
           'CPU-bus.csv','CPU-ordinary.sfc','CPU-packets.hex','nes_output264.c']:
  assert pin(q/n).read_bytes()==pin(prior/'test01'/n).read_bytes(),n
 elf_differences=[]
 with pin(q/'output.elf').open('rb') as f,pin(prior/'test01/output.elf').open('rb') as g:
  ef,eg=ELFFile(f),ELFFile(g)
  assert ef.header==eg.header
  assert ef.num_sections()==eg.num_sections()
  for section in ef.iter_sections():
   before=eg.get_section_by_name(section.name);assert section.header==before.header
   if section.data()!=before.data():
    assert section.name=='.strtab' and section['sh_flags']==0
    # GCC's temporary assembly-object filename is a nonloaded STT_FILE name.
    pattern=rb'cc[A-Za-z0-9]{6}\.o'
    assert len(re.findall(pattern,section.data()))==len(re.findall(pattern,before.data()))==1
    assert re.sub(pattern,b'ccTEMP00.o',section.data())==re.sub(pattern,b'ccTEMP00.o',before.data())
    elf_differences.append(dict(section=section.name,flags=0,reason='temporary assembler object filename only'))
 assert sum(int(x.split()[2]) for x in (q/'blocks.txt').read_text().splitlines())==83240
 # Unmodified SPI endpoint and ARM serializer guards are reused only with
 # file hashes, not by claiming new executions.
 spi=read(prev/'spiguards01/result.json')
 for n,h in spi['rtl_hashes'].items():assert sha(pin(q/n))==h
 armguard=read(prior/'armguards01/result.json')
 assert pin(q/'nes_output264.c').read_bytes()==pin(prior/'arm01/nes_output264.c').read_bytes()
 assert sha(pin(prior/'arm01/output.elf'))==armguard['ELF_sha256']
 ev=events(q);times=done(ev);arm={x['frame']:x for x in results['test03']['ARM']['frames']}
 assert len(times)==71 and sum(x[0]=='cpu267' for x in ev)==544
 assert sum(x[0]=='receipt' for x in ev)==2069
 assert max(int(x[2]) for x in ev if x[0]=='credits')==4
 sc={int(x['frame']):x for x in rows(q/'cycles.csv')}
 oldsc={int(x['frame']):x for x in rows(prior/'test01/cycles.csv')}
 assert set(sc)==set(oldsc)
 assert all(sc[f]['queries']==oldsc[f]['queries'] for f in sc)
 source_deltas={k:dict(min=min(int(sc[f][k])-int(oldsc[f][k]) for f in sc),
                       max=max(int(sc[f][k])-int(oldsc[f][k]) for f in sc))
                for k in ['total','prepare','blocked','ackwait','transfer','overlap']}
 out=[]
 for f in range(905,976):
  expected=packets(pin(prior/f'arm01/frame{f}.packets'))
  actual=[bytes.fromhex(x['tx'])[1:-2] for x in read(q/f'arm{f}.json')['transfers'] if x['tx'].startswith('e1')]
  assert actual==expected and all(16<=len(p)<=256 for p in actual)
  ct=collections.Counter();wire=collections.Counter();instructions=0
  for x in ev:
   if x[0]=='arm267' and int(x[1])==f:
    ct[int(x[2])]+=1;wire[int(x[2])]+=int(x[3]);instructions+=int(x[5])
  assert wire[225]==sum(len(p)+3 for p in actual)
  assert sum(wire.values())==arm[f]['SPI_bytes']
  sm=int(sc[f]['total'])*45.454/1e6;total=sm+times[f]
  prior_transactions=sum(int(old[f][k]) for k in ['packets','E0_full','E2_short','E8_polls','E9_batches','EA_retire'])
  delta=(sum(wire.values())-int(old[f]['SPI_bytes']))*8/2625+\
        (instructions-int(old[f]['ARM_IRQ_event_instructions']))/84000+\
        (sum(ct.values())-prior_transactions)*.008
  out.append(dict(frame=f,source_ms=sm,output_schedule_ms=times[f],diagnostic_serial_ms=total,
   prior274_ms=float(old[f]['diagnostic_serial_ms']),delta274_ms=total-float(old[f]['diagnostic_serial_ms']),
   prior275_ms=float(inline[f]['diagnostic_serial_ms']),delta275_ms=total-float(inline[f]['diagnostic_serial_ms']),
   budget_gap_ms=total-1000/60,E1_wire=wire[225],reference_wire_extra=0,
   E0_full=ct[224],E2_short=ct[226],SPI_bytes=sum(wire.values()),prior274_SPI_bytes=int(old[f]['SPI_bytes']),
   ARM_instructions=arm[f]['instructions'],ARM_IRQ_event_instructions=instructions,
   prior274_ARM_IRQ_event_instructions=int(old[f]['ARM_IRQ_event_instructions']),
   transaction_delta=sum(ct.values())-prior_transactions,wire_instruction_transaction_delta_ms=delta,
   remaining_schedule_delta_ms=total-float(old[f]['diagnostic_serial_ms'])-delta,
   E8=ct[232],E9=ct[233],EA=ct[234]))
 with (d/'costs.csv').open('w',newline='') as h:
  w=csv.DictWriter(h,fieldnames=list(out[0]),lineterminator='\n');w.writeheader();w.writerows(out)
 we=events(b/'window01');oe=events(prior/'window01');ie=events(prev/'window01')
 ws={int(x['frame']):x for x in rows(b/'window01/cycles.csv')}
 def old_window(r):return {x['frame']:x['diagnostic_serial_ms'] for x in r['restricted_ROM']}
 w274=old_window(p274);w275=old_window(p275);window=[]
 for f,t in done(we).items():
  total=int(ws[f]['total'])*45.454/1e6+t
  lines=[x for x in we if x[0]=='arm267' and int(x[1])==f]
  window.append(dict(frame=f,diagnostic_serial_ms=total,prior274_ms=w274[f],delta274_ms=total-w274[f],
   prior275_ms=w275[f],delta275_ms=total-w275[f],budget_gap_ms=total-1000/60,
   E2=sum(int(x[2])==226 for x in lines),SPI_bytes=sum(int(x[3]) for x in lines),
   ARM_IRQ_event_instructions=sum(int(x[5]) for x in lines)))
 def end(ev):return max(int(x[2]) for x in ev if x[0]=='frame_done')/1e9
 sequence=dict(current_end_ms=end(we),prior274_end_ms=end(oe),prior275_end_ms=end(ie),
  delta274_ms=end(we)-end(oe),delta275_ms=end(we)-end(ie))
 def mapping(folder):
  s=pin(folder/'output_files/board.map.summary').read_text();values={}
  for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),
                  ('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]:
   values[k]=int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',s).group(1).replace(',',''))
  rpt=pin(folder/'output_files/board.map.rpt').read_text();ent={};own={}
  for line in rpt.splitlines():
   fields=[v.strip() for v in line.split(';')]
   if len(fields)==14 and re.fullmatch(r'\d+ \(\d+\)',fields[2]):
    own[fields[10]]={k:int(re.search(r'\((\d+)\)',fields[i]).group(1)) for k,i in [('comb',2),('FF',3)]}
    if fields[-3] in ['nes_output260','nes_queue260','nes_core257']:ent[fields[-3]]=dict(comb=fields[2],FF=fields[3],RAM_bits=fields[4])
  assert {k:sum(v[k] for v in own.values()) for k in ['comb','FF']}=={k:values[k] for k in ['comb','FF']}
  return values,ent,own
 m,entities,own=mapping(b/'board01');om,oe2,oldown=mapping(BASE/'probes/nes-joint270/board02')
 im,_,_=mapping(prev/'board01');changes=[]
 for key in sorted(own.keys()|oldown.keys()):
  before=oldown.get(key,dict(comb=0,FF=0));after=own.get(key,dict(comb=0,FF=0))
  if before!=after:changes.append(dict(path=key,before=before,after=after,delta={k:after[k]-before[k] for k in before}))
 assert sum(x['delta']['comb'] for x in changes)==m['comb']-om['comb']
 region=[k for k in own if k.endswith(('nes_core257:encoder','nes_output260:flow','nes_queue260:queue'))]
 assert len(region)==3
 region_comb=sum(own[k]['comb'] for k in region)
 region_delta=sum(own[k]['comb']-oldown[k]['comb'] for k in region)
 assert m==dict(LE=22986,comb=18245,FF=8832,RAM_bits=303712)
 assert region_comb==5527 and region_delta==591
 rpt=(b/'board01/output_files/board.map.rpt').read_text()
 core_state_line=next(x for x in rpt.splitlines() if '; Name ' in x and 'state.P_LOAD' in x and 'state.WAITACK' in x)
 extracted_states=[x.strip() for x in core_state_line.split(';') if x.strip().startswith('state.')]
 assert len(extracted_states)==56
 assert 'nes_core257:encoder|state' in rpt and 'nes_output260:flow|state' in rpt
 assert len(results['guards01']['guards'])==49
 warm=[x for x in out if x['frame']>=907]
 r=dict(passed=True,stage=276,scope=__doc__,selected=selected,frames=71,
  reference_program_transmitted=False,shared_source_query_descriptor_receipt_FSM=True,
  source_query_prefetch_preserved=True,changed_RTL=changed,packets=1231,source_bytes=83240,
  source_cycle_deltas274=source_deltas,source_query_counts_identical274=True,
  map_ranges=2069,map_bytes=13406,map_tile_DMA_bytes=26350,metadata_per_frame=8570,receipt_per_frame=754,
  CRC_per_frame=64,ordinary_CPU_trace_commands=544,max_credit=4,
  warm_max=max(warm,key=lambda x:x['diagnostic_serial_ms']),
  warm_over=sum(x['diagnostic_serial_ms']>1000/60 for x in warm),
  over_frames=[x['frame'] for x in warm if x['diagnostic_serial_ms']>1000/60],
  frame954=next(x for x in out if x['frame']==954),restricted_ROM=window,restricted_sequence=sequence,
  SPI=dict(total=sum(x['SPI_bytes'] for x in out),prior274_total=sum(int(v['SPI_bytes']) for v in old.values()),
   prior275_total=sum(int(v['SPI_bytes']) for v in inline.values()),extra_reference_wire=0,
   E0=sum(x['E0_full'] for x in out),E2=sum(x['E2_short'] for x in out),
   E8=sum(x['E8'] for x in out),E9=sum(x['E9'] for x in out),EA=sum(x['EA'] for x in out),
   prior274_E2=sum(int(x['E2_short']) for x in old.values()),
   prior274_E8=sum(int(x['E8_polls']) for x in old.values())),
  MAP=dict(current=m,prior270_274=om,prior275=im,delta274={k:m[k]-om[k] for k in m},
   delta275={k:m[k]-im[k] for k in m},entities=entities,prior_entities=oe2,own_changes=changes,
   core_FSM_extracted_states=extracted_states,host_FSM_extracted=True,
   region_core_host_queue_comb=region_comb,region_delta274=region_delta,
   other_synthesis_delta=m['comb']-om['comb']-region_delta,retained_other_comb=m['comb']-region_comb,
   region_budget_if_others_fixed=15408-m['comb']+region_comb,
   required_region_reduction_percent=(m['comb']-15408)/region_comb*100,
   comb_deficit=m['comb']-15408,FIT=False,STA=False),board_binding=board_diffs,
  ARM=dict(full=pin(q/'size-rom.log').read_text(),live_stack=results['test03']['ARM']['stack_observed'],
   IRQ_bodies=len(results['test03']['ARM']['IRQ_cases']),runtime_sections_identical274=True,
   full_ELF_identical274=not elf_differences,ELF_differences=elf_differences),
  guards=results['guards01']['guards'],reused_SPI_guards=spi['log'],reused_ARM_guards=armguard,
  full_path_ms=None,P2_selected=False,physical=False,full_RUN=False,actual_SNES_live=False,
  input_hashes=pins,script_sha256=sha(Path(__file__)))
 (d/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({k:r[k] for k in ('passed','warm_max','restricted_ROM','restricted_sequence','SPI','ARM')},indent=2))
 print(json.dumps({k:r['MAP'][k] for k in ('current','delta274','delta275','entities','comb_deficit')},indent=2))

if __name__=='__main__':main()
