# SPDX-License-Identifier: MIT
"""Joint area envelope and measured retained SNES work; no full-path approval."""
from pathlib import Path
import argparse,csv,json,shutil
from collections import defaultdict
from nes_delta231 import ROOT,BASE,sha
from analyze_nes_schedule248 import simulate,replace_map_packets,MASTER_MS
from analyze_nes_spantrade247 import spans,encode as mapencode
from analyze_nes_mapjoint247 import bitmap
from analyze_nes_validation247 import manifest_wire

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
 P=BASE/'probes/nes-joint250';old=BASE/'probes/nes-wholepath247';pins={}
 def pin(f):pins[f.relative_to(BASE).as_posix()]=sha(f);return f
 def read(f):return json.loads(pin(f).read_text(encoding='utf-8'))
 snes=read(P/'snes01/result.json');receipt=read(P/'receipt02/result.json');area=read(P/'map02/result.json')
 assert snes['passed'] and snes['commits']==71 and receipt['passed'] and area['passed']
 assert sha(pin(P/'receipt02/nes_receipt250.sv'))==sha(pin(P/'map02/nes_receipt250.sv'))==receipt['rtl_sha256']
 assert pin(P/'receipt02/cycles.csv').read_bytes()==pin(P/'receipt01/cycles.csv').read_bytes()
 for name,h in receipt['input_hashes'].items():assert sha(pin(BASE/name))==h
 for name,h in area['input_hashes'].items():assert sha(pin(BASE/name))==h
 for name,h in snes['inputs'].items():assert sha(BASE/name)==h
 # Same product bytes and independent output oracles; callbacks only.
 prior=read(old/'jointdecode-test02/result.json')
 for k in ('commits','acks','retired_chunks','max_dma','vram_bytes','vram_commands','largest_list','single_vblank_commits'):assert snes[k]==prior[k],k
 for f in (old/'jointdecode-test02/run').glob('expected-*.bin'):assert sha(pin(P/'snes01/run'/f.name))==sha(pin(f)),f.name
 pp=defaultdict(list)
 for f in sorted((P/'snes01/run').glob('req-*.bin')):
  b=pin(f).read_bytes();assert b==pin(old/'jointdecode-test02/run'/f.name).read_bytes();pp[int.from_bytes(b[8:10],'little')].append(b)
 events=defaultdict(list)
 for r in csv.DictReader(pin(P/'snes01/run/retained250.csv').open()):events[int(r['generation']),int(r['ordinal'])].append(r)
 marks=defaultdict(list);validates={};measured=[]
 for (g,ordinal),rr in sorted(events.items()):
  last={r['event']:int(r['clock']) for r in rr}
  if 'validate181' in last:assert g not in validates;validates[g]=last['validate181_return0']-last['validate181']
  if 'mark212' not in last:continue
  start=last['mark212'];end=last['mark212_return0'];bits=next((int(x['clock']) for x in rr if x['event']=='bits212'),None)
  if bits is not None:assert start<=bits<last['address250']<=end
  r=dict(frame=g+904,ordinal=ordinal,op=int(rr[0]['op']),section=int(rr[0]['section']),mark_clocks=end-start,
   bitmap_clocks=last['address250']-bits if bits is not None else 0,
   command_tail_clocks=end-last['address250'] if bits is not None else end-start)
  r['retained_without_bitmap_clocks']=r['mark_clocks']-r['bitmap_clocks'];marks[g].append(r);measured.append(r)
 assert len(validates)==71
 corecycles={int(r['frame']):int(r['cycles']) for r in csv.DictReader(pin(P/'receipt02/cycles.csv').open())}
 old249=read(BASE/'probes/nes-joint249/analysis02/result.json')
 reference={(r['frame'],r['map_format'],r['map_setup_clocks']):r for r in old249['rows'] if r['codec']=='block' and r['nonmap_service_clocks']==500}
 place={r['frame']:r for r in read(old/'placement05/result.json')['rows'] if r['placement']=='FPGA_typed_ext16'}
 jp={(int(r['frame']),r['mode']):r for r in csv.DictReader(pin(old/'validation-analysis02/joint-frames.csv').open())}
 wire={r['frame']:r['source_spi_bytes'] for r in old249['wire_rows'] if r['codec']=='block'}
 previous=bytes(4096);stale=[set(range(2048)),set(range(2048))];rows=[];frames=[]
 for g in range(1,72):
  frame=g+904;bank=(g-1)%2
  nonmap=[b for b in pp[g] if b[0] in (2,4,5,7,8)]
  assert len(nonmap)==len(marks[g]);assert [(b[0],b[1]) for b in nonmap]==[(r['op'],r['section']) for r in marks[g]]
  current=pin(old/f'jointdecode-test02/run/expected-{g}.bin').read_bytes()[:4096];change={i for i in range(2048) if current[2*i:2*i+2]!=previous[2*i:2*i+2]}
  for st in stale:st.update(change)
  frames.append(dict(frame=frame,validate_clocks=validates[g],validate_ms=validates[g]/MASTER_MS,command_tail_clocks=sum(r['command_tail_clocks'] for r in marks[g]),retained_without_bitmap_clocks=sum(r['retained_without_bitmap_clocks'] for r in marks[g]),receipt_core_cycles=corecycles[frame]))
  for gap in (16,):
   fmt='exact64' if gap==0 else 'gap16_64';rr=spans(stale[bank],gap,64);bm=bitmap({w for at,n in rr for w in range(at//2,(at+n)//2)});mf=manifest_wire(bm);compressed=sum(len(b)+19 for at,b in mf)<294
   if not compressed:mf=[(0,bm[:240]),(240,bm[240:])]
   replacement=replace_map_packets(pp[g],mapencode(rr,current,True),mf,compressed)
   placement=dict(place[frame]);placement['ready4_bytes']=int(jp[frame,'packed_'+fmt]['ready4'])+99*placement['chunks']+32+wire[frame]-placement['source_spi_bytes']
   placement.update(source_spi_bytes=wire[frame],runs=len(rr),staging_payload_normalization_ms=sum(n for at,n in rr)*8/MASTER_MS,seal_coverage_tail_ms=0)
   if frame<907:continue
   for setup in (500,1000):
    ref=reference[frame,fmt,setup]
    for mode,key in [('command_tail','command_tail_clocks'),('only_bitmap_removed','retained_without_bitmap_clocks')]:
     row,_=simulate(frame,replacement,[r[key]/MASTER_MS for r in marks[g]],placement,setup,False)
     parser=8*sum(len(b) for b in replacement if b[0] not in (1,7))/22000
     # Use only the gap16 ranges actually executed by the receipt core.
     core=corecycles[frame]/22000
     total=row['total_ms']+ref['source_prepare_ms']+parser+core+ref['final_fixed_allocated_ms']+validates[g]/MASTER_MS
     rows.append(dict(frame=frame,map_format=fmt,map_setup_clocks=setup,retained_policy=mode,total_ms=total,residual_ms=1000/60-total,old249_total_ms=ref['total_ms'],validate_ms=validates[g]/MASTER_MS,receipt_core_ms=core,receipt_matches_map=gap==16,parser_allocated_ms=parser,source_prepare_ms=ref['source_prepare_ms'],new_consumer_executed=False))
  stale[bank].clear();previous=current
 summaries={}
 for fmt in ('gap16_64',):
  for setup in (500,1000):
   for mode in ('command_tail','only_bitmap_removed'):
    rr=[r for r in rows if (r['map_format'],r['map_setup_clocks'],r['retained_policy'])==(fmt,setup,mode)]
    summaries[f'{fmt}_{setup}_{mode}']=dict(max_ms=max(r['total_ms'] for r in rr),min_residual_ms=min(r['residual_ms'] for r in rr),over=[r['frame'] for r in rr if r['residual_ms']<0],worst=max(rr,key=lambda r:r['total_ms']))
 for name in ('measure_nes_retained250.py','nes_receipt250.py','probe_nes_receipt250.py','nes_block249_rtl.py','analyze_nes_schedule248.py','analyze_nes_spantrade247.py'):pin(ROOT/'tools'/name)
 result=dict(passed=True,stage=250,scope=__doc__,frames=71,schedules=len(rows),retained_intervals=len(measured),snes={k:v for k,v in snes.items() if k!='inputs'},receipt={k:v for k,v in receipt.items() if k!='input_hashes'},area={k:v for k,v in area.items() if k!='input_hashes'},
  validate_warm_ms=[min(f['validate_ms'] for f in frames[2:]),max(f['validate_ms'] for f in frames[2:])],summaries=summaries,
  rows=rows,frames_detail=frames,input_hashes=pins,script_sha256=sha(Path(__file__)),
  limitations=['Receipt core and249 source separately tested;joint MAP envelope has separate inputs,not actual full pipeline.',
   'Parser/CRC/epoch/token/certificate,collector semantic query/projector,FIFO read arbitration and CDC still excluded from new area.',
   'Existing SNES execution observed;removing checks in schedule is counterfactual,no new consumer executed.',
   'Only gap16 receipt ranges are used in this follow-up schedule.',
   'Parser8cycles/byte,map setup and final2000master clocks remain allocations;fullARM/query/ordinaryDMA/dispatch/polls/gaps/VBlank consume residual.',
   'No full-board FIT/STA,physical60fps or installable firmware.'])
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');public={k:v for k,v in result.items() if k not in ('rows','frames_detail','input_hashes')};public.update(input_count=len(pins),private_result_sha256=sha(d/'result.json'))
 (d/'summary.json').write_text(json.dumps(public,indent=2)+'\n')
 for name,rr in [('schedules.csv',rows),('frames.csv',frames),('retained.csv',measured)]:
  with (d/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rr[0]),lineterminator='\n');w.writeheader();w.writerows(rr)
 shutil.copyfile(__file__,d/'analyzer.py')
 print(json.dumps(dict(validate_warm_ms=result['validate_warm_ms'],summaries=summaries),indent=2))

if __name__=='__main__':main()
