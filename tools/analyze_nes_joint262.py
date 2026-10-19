# SPDX-License-Identifier: MIT
"""Compare separate/shared H2 CDC on matching actual source/map boundaries.

900-clock bus service is a cold CPU-derived sensitivity; no full-path bound.
"""
import argparse,csv,hashlib,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_joint262 import sources
from probe_nes_joint262 import tb
from probe_nes_joint261 import packets


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve();assert not out.exists();out.mkdir(parents=True)
 base=BASE/'probes/nes-joint262';pins={}
 def pin(f):pins[f.relative_to(BASE).as_posix()]=sha(f);return f
 def result(name):return json.loads(pin(base/name/'result.json').read_text(encoding='utf-8'))
 arm=result('arm01');guard=result('arm-guards02');separate=result('test02');shared=result('test05');m1=result('map01');m2=result('map02')
 expected_guards=[[kind,n] for kind in ['NEG','PRENEG'] for n in range(1,7)]
 partial=result('partial01');assert partial['passed'] and partial['context_bytes_before_STOP']==8 and partial['BEGIN_count']==0
 for n,h in partial['rtl_hashes'].items():assert h==shared['rtl_hashes'][n]==sha(pin(base/'partial01'/n))
 assert partial['TB_sha256']==sha(pin(base/'partial01/joint262_tb.sv'))
 assert 'PASS JOINT262 PRENEG=5 context=8 begins=0' in pin(base/'partial01/vsim.log').read_text()
 for name,r,sharing in [('test03',separate,False),('test05',shared,True)]:
  assert r['passed']
  if sharing:assert r['frames']==71 and r['guards']==expected_guards
  else:assert 'PASS JOINT262 frames=71 batches=124 ranges=2069 map_bytes=13406' in pin(base/name/'vsim.log').read_text()
  for n,h in r['rtl_hashes'].items():assert sha(pin(base/name/n))==h,(name,n)
  for n,s in sources(sharing).items():assert hashlib.sha256(s.encode()).hexdigest()==r['rtl_hashes'][n],(name,n)
  expected_tb=tb() if sharing else tb().replace('if(!RPC&&!NEG&&(PRENEG==0||PRENEG==6))begin','if(!RPC&&!NEG&&!PRENEG)begin')
  assert pin(base/name/'joint262_tb.sv').read_text(encoding='utf-8')==expected_tb
  for key,h in r['input_hashes'].items():
   f=BASE/key
   # Versioned runners are copied at launch: preserve an older baseline
   # snapshot if the shared-control implementation changed the current tool.
   if sha(f)!=h and key.startswith('repository-nes-milestone/tools/'):
    f=base/name/Path(key).name
   assert sha(pin(f))==h,(name,key)
  for kind,n in expected_guards:
   if not sharing and kind=='PRENEG' and n==6:
    log=pin(base/name/'preneg06/vsim.log').read_text(errors='replace');assert 'PASS JOINT262 PRENEG=6' not in log
    continue
   log=pin(base/name/f'{kind.lower()}{n:02}'/'vsim.log').read_text(errors='replace')
   assert f'PASS JOINT262 {kind}={n}' in log and '** Fatal:' not in log
  for f in (base/name).glob('*.log'):pin(f)
  flat={}
  for line in pin(base/name/'blocks.txt').read_text().splitlines():
   frame,tok,n,b=line.split();flat.setdefault(int(frame),bytearray()).extend(bytes.fromhex(b))
  assert len(flat)==71
  for frame,b in flat.items():
   oracle=BASE/'probes/nes-joint249/blocktest03';size=int(pin(oracle/f'frame{frame}.meta').read_text().split()[0]);assert b==bytes.fromhex(pin(oracle/f'frame{frame}.expected.hex').read_text())[:size]
 for n in ['cycles.csv','joint-events.csv','blocks.txt']:assert (base/'test03'/n).read_bytes()==(base/'test05'/n).read_bytes(),n
 for name,r,ref in [('map01',m1,separate),('map02',m2,shared)]:
  assert r['passed'] and 'Lite Edition' in r['summary']
  for n,h in r['rtl_hashes'].items():assert sha(pin(base/name/n))==h==ref['rtl_hashes'][n]
  pin(base/name/'output_files/joint.map.rpt');pin(base/name/'output_files/joint.map.summary');pin(base/name/'map.log')
 assert m1['test_sha256']==sha(pin(base/'test02/result.json'))
 assert m2['test_sha256']==sha(pin(base/'test04/result.json'))
 assert arm['passed'] and len(arm['frames'])==71 and guard['passed'] and len(guard['cases'])==12 and len(guard['preflight'])==6
 assert arm['source_sha256']==sha(pin(ROOT/'tools/nes_output262.c'))
 assert arm['ELF_sha256']==guard['ELF_sha256']==sha(pin(base/'arm01/output.elf'))
 for f in (base/'arm01').glob('*.log'):pin(f)
 for f in (base/'arm01').glob('*.su'):pin(f)
 def events(d):
  e={f:dict(receipts=[]) for f in range(905,976)}
  for line in pin(d/'joint-events.csv').read_text().splitlines():
   kind,fr,at,value=line.split(',');v=e[int(fr)]
   if kind=='receipt':v['receipts'].append(int(value)/1000)
   elif kind=='prelude_done':v['prelude_done']=int(at)/1e9
   elif kind=='maps_done':v['maps_done']=int(at)/1e9
   elif kind=='frame_done':v['end']=int(at)/1e9;v['output_ms']=int(value)/1e9
  return e
 se=events(base/'test03');sh=events(base/'test05');old=events(BASE/'probes/nes-joint261/test05')
 def cycles(d):return {int(r['frame']):r for r in csv.DictReader(pin(d/'cycles.csv').open())}
 cy=cycles(base/'test05');oldcy=cycles(BASE/'probes/nes-joint261/test05')
 oldarm=json.loads(pin(BASE/'probes/nes-batch260/arm01/result.json').read_text());oldar={r['frame']:r for r in oldarm['frames']}
 def area(r):
  return {k:int(re.search(label+r'\s*:\s*([\d,]+)',r['summary'])[1].replace(',','')) for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
 ar1=area(m1);ar2=area(m2);rows=[];totctx=0
 def inclusive(name):
  lines=(base/'map02/output_files/joint.map.rpt').read_text().splitlines()
  line=next(s for s in lines if s.startswith(';    |'+name+'|'))
  fields=[x.strip() for x in line.split(';')]
  return dict(comb=int(fields[2].split()[0]),FF=int(fields[3].split()[0]),RAM_bits=int(fields[4]))
 core=inclusive('nes_joint257:core');flow=inclusive('nes_output260:flow')
 newledger={k:core[k]+flow[k] for k in core};oldledger=dict(comb=3336,FF=2084,RAM_bits=98560)
 pin(ROOT/'analysis/joint261-verification.json')
 for ar,m in zip(arm['frames'],shared['map_frames']):
  f=ar['frame'];assert f==m['frame'];pr=oldar[f]
  assert ar['SPI_bytes']==pr['SPI_bytes'] and ar['status_reads']==pr['status_reads'] and ar['packets']==pr['packets']
  pp=packets(pin(base/f'arm01/frame{f}.packets'));assert [p[0] for p in pp[:2]]==[13,1]
  ctx=bytes.fromhex(pin(base/f'test05/prelude{f}.hex').read_text());assert ctx==b''.join(pp[:2]);totctx+=len(pp[0][16:])
  priorpp=packets(pin(BASE/f'probes/nes-batch260/arm01/frame{f}.packets'))
  assert pp[0][16:]==next(p[16:] for p in priorpp if p[0]==13)
  assert len(sh[f]['receipts'])==m['ranges']==len(se[f]['receipts'])
  for col in ['prepare','queries','overlap']:assert cy[f][col]==oldcy[f][col],(f,col)
  e=sh[f];delta=ar['ARM_instructions']-pr['ARM_instructions']
  rows.append(dict(frame=f,map_ranges=m['ranges'],batch_packets=m['packets'],batch_wire_bytes=m['wire_bytes'],
   ARM_instructions=ar['ARM_instructions'],ARM_instruction_delta260=delta,ARM_delta_CPI1_us=delta/84,
   ARM_SPI_bytes=ar['SPI_bytes'],ARM_SPI_delta260=0,
   output_separate900_ms=se[f]['output_ms'],output_shared900_ms=e['output_ms'],shared_minus_separate_ms=e['output_ms']-se[f]['output_ms'],
   prior261_fixture_context500_ms=old[f]['output_ms'],combined_context_and_service_change_ms=e['output_ms']-old[f]['output_ms'],
   source_done_to_BEGIN_ready_ms=e['prelude_done']-(e['end']-e['output_ms']),
   final_validation_ACK_tail_ms=e['end']-e['maps_done'],receipt_max_ns=max(e['receipts']),
   source_cycle_delta261=int(cy[f]['total'])-int(oldcy[f]['total']),
   full_ARM_nonmap_ROM_VBlank_ms=None,whole_board_LE_margin=None))
 with (out/'costs.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
 report=dict(passed=True,stage='NES262',frames=71,H2_context_bytes=totctx,source_bytes=shared['source_bytes'],
  map_ranges=sum(r['map_ranges'] for r in rows),batch_packets=sum(r['batch_packets'] for r in rows),guards=expected_guards,
  partial_context_STOP=dict(accepted_bytes=8,BEGIN_count=0,RAM_frozen_bytes=1024),same_service_trace_byte_exact=True,
  ARM=dict(text=2320,bss=312,observed_stack=arm['stack_observed'],delta_text260=76,delta_bss260=0,
   instruction_delta_range=[min(r['ARM_instruction_delta260'] for r in rows),max(r['ARM_instruction_delta260'] for r in rows)],
   total_wire_delta260=0,preflight_guards=guard['preflight'],counter_wrap=guard['counter_wrap'],full_RUN=False),
  MAP=dict(separate=ar1,shared=ar2,delta_shared_separate={k:ar2[k]-ar1[k] for k in ar2},
   prior261=dict(LE=7141,comb=5665,FF=2788,RAM_bits=90368),whole_board=False,FIT=False,STA=False),
  replacement_ledger=dict(old_excluding_lease=oldledger,new_excluding_lease_and_top=newledger,
   arithmetic_delta={k:newledger[k]-oldledger[k] for k in core},same_synthesis_boundary=False,proven_whole_LE_reclaim=0),
  same_service_delta_ms=[min(r['shared_minus_separate_ms'] for r in rows),max(r['shared_minus_separate_ms'] for r in rows)],
  scope='H2 context and BEGIN ACK enter actual core via shared24-bit consumed mailbox; other ordinary producers remain fixtures',
  setup=dict(master_clocks=900,source='261 cold CPU beyond nominal DMA900..948',is_WCET=False,token_bus_writes_charged_separately=True),
  full_path_ms=None,physical60fps=False,P2_selected=False,
  heavy=[r for r in rows if r['frame'] in [905,907,952,954,955,962,963,968,970]],
  preserved_experiments=dict(test01='declaration-order compilation failure',test03='71 normal and11guards pass; PRENEG6 harness disabled DMA service, stopped; final shared run uses corrected harness'),
  limitations=['ARM instructions executed separately; H2/BEGIN bytes replayed, map sequence/token rebound','BEGIN exact payload check uses bus service model; no actual full65816 executor','freshscroll/rawtail/manifest/nonmap stream still fixture producers','source and output share actual SPI but full ARM N5/planner/RUN/IRQ not bound','900clock service is sensitivity, not warm physical WCET; no new full-path timing','tile192/ROM contention and whole board FIT/STA/CDC/IO remain open'],
  input_hashes=pins)
 (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ['input_hashes','heavy']},indent=2))


if __name__=='__main__':main()
