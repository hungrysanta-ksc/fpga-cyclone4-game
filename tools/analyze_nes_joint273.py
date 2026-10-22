# SPDX-License-Identifier: MIT
"""Compare ARM program layouts against the same whole-board removal budget.

Only producer instructions are newly executed. Wire/setup arithmetic and an
unchanged-poll serial addition are sensitivities, not a retimed RTL schedule.
"""
from pathlib import Path
import argparse,csv,json,math,re
from nes_delta231 import ROOT,BASE,sha
from analyze_nes_boundary269 import hierarchy

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--producer',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
 a=ap.parse_args();p=a.producer.resolve();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
 pins={}
 def pin(q):pins[str(q)]=sha(q);return q
 def read(q):return json.loads(pin(q).read_text(encoding='utf-8'))
 r=read(p/'result.json');assert r['passed'] and r['producer_executions']==213
 assert r['source_sha256']==sha(pin(ROOT/'tools/nes_primitive273.c'))==sha(pin(p/'nes_primitive273.c'))
 assert pin(p/'probe_nes_primitive273.py').read_bytes()==pin(ROOT/'tools/probe_nes_primitive273.py').read_bytes()
 assert r['ELF_sha256']==sha(pin(p/'output.elf'))
 assert len(r['directed_codec_cases'])==7 and r['decoder_negative_cases']==17
 baseline={int(x['frame']):x for x in csv.DictReader(pin(ROOT/'analysis/joint270-costs.csv').open())}
 source={int(x['frame']):x for x in csv.DictReader(pin(ROOT/'analysis/joint269-source-candidates.csv').open())}
 rows=[];overflow=[];max_program=0
 for original in r['rows']:
  x=dict(original);f=x['frame'];b=baseline[f]
  x['layout']='separate_program'
  rows.append(x)
  if x['mode']=='refs16':
   q=BASE/f'probes/nes-joint270/test05/arm{f}.json'
   assert r['pins'][str(q)]==sha(pin(q))
   packets=[bytes.fromhex(t['tx'])[1:-2] for t in read(q)['transfers'] if t['tx'].startswith('e1')]
   programs=read(p/f'frame{f}-2.json');assert len(packets)==len(programs)
   added=extra=inline=0
   for packet,z in zip(packets,programs):
    program=bytes.fromhex(z['program']);n=len(program);max_program=max(max_program,n)
    if not n:continue
    if len(packet)+2+n<=256:added+=2+n;inline+=1
    else:
     chunks=math.ceil(n/238);added+=n+21*chunks;extra+=chunks
     overflow.append(dict(frame=f,sequence=z['sequence'],op=z['op'],packet_bytes=len(packet),
                          program_bytes=n,required_slot_bytes=len(packet)+2+n))
   y=dict(x,layout='inline_when_fits',proposed_E1_wire=x['original_E1_wire']+added,
          delta_wire=added,delta_transactions=extra,inline_packets=inline)
   y['wire_delta_ms']=added*8/2625;y['setup_delta_ms']=extra*.008
   y['additive_sensitivity_ms']=y['producer_CPI1_ms']+y['wire_delta_ms']+y['setup_delta_ms']
   rows.append(y)
 for x in rows:
  f=x['frame'];b=baseline[f];s=source[f]
  x.setdefault('inline_packets',0)
  x['baseline270_serial_ms']=float(b['diagnostic_serial_ms'])
  x['unchanged_poll_serial_sensitivity_ms']=x['baseline270_serial_ms']+x['additive_sensitivity_ms']
  x['serial_sensitivity_gap_ms']=x['unchanged_poll_serial_sensitivity_ms']-1000/60
  x['source_wire_plus_E1_floor_ms']=(int(b['source_SPI_bytes'])+x['proposed_E1_wire'])*8/2625
  x['mask_source_payload_plus_E1_floor_ms']=(int(s['mask_payload'])+x['proposed_E1_wire'])*8/2625
  x['literal_source_payload_plus_E1_floor_ms']=(4398+int(s['raw_bytes'])+x['proposed_E1_wire'])*8/2625
 report=pin(BASE/'probes/nes-joint270/board02/output_files/board.map.rpt')
 h=hierarchy(report)
 blocks={n:h[n]['comb'] for n in [
  '|nes_core257:encoder|','|nes_transport257:transport|','|nes_queue260:queue|',
  '|nes_plan_spi200:endpoint|','|nes_plan_batch206:transport|','|nes_spi270:spi_front270|']}
 blocks['|nes_output260:flow| exclusive']=h['|nes_output260:flow|']['own_comb']
 assert sum(blocks.values())==6486
 core=blocks['|nes_core257:encoder|'];flow=blocks['|nes_output260:flow| exclusive']
 assert core==2448 and flow==2206
 rtl=pin(BASE/'probes/nes-joint270/board02/nes_core257.sv').read_text()
 states=re.search(r'typedef enum logic\[5:0\] \{(.*?)\} state_t;',rtl,re.S).group(1).replace('\n','').replace(' ','').split(',')
 assert len(states)==42
 summary={}
 for mode,layout in [('event24','separate_program'),('runs16','separate_program'),('refs16','separate_program'),('refs16','inline_when_fits')]:
  warm=[x for x in rows if x['frame']>=907 and x['mode']==mode and x['layout']==layout]
  summary[mode+'/'+layout]=dict(
   warm_delta_wire_range=[min(x['delta_wire'] for x in warm),max(x['delta_wire'] for x in warm)],
   warm_instructions_range=[min(x['producer_instructions'] for x in warm),max(x['producer_instructions'] for x in warm)],
   warm_additive_ms_range=[min(x['additive_sensitivity_ms'] for x in warm),max(x['additive_sensitivity_ms'] for x in warm)],
   warm_serial_sensitivity_over=sum(x['serial_sensitivity_gap_ms']>0 for x in warm),
   warm_literal_E1_floor_over=sum(x['literal_source_payload_plus_E1_floor_ms']>1000/60 for x in warm),
   examples=[x for x in warm if x['frame'] in (907,954,970)])
 fields=list(dict.fromkeys(k for x in rows for k in x))
 with (d/'costs.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
 result=dict(passed=True,scope=__doc__,frames=71,packets=r['packets'],semantic_events=r['semantic_events'],
  ARM=dict(text=2032,bss=64,observed_stack=r['stack_observed'],guard_executions=r['guard_executions'],
   decoder_negatives=r['decoder_negative_cases'],directed_executions=r['directed_codec_executions']),
  binding_counterexample=r['binding_counterexample'],
  summary=summary,reference_max_program_bytes=max_program,inline_overflow=overflow,
  inline_only_all71_supported=not overflow,whole270_disjoint_comb=blocks,region_comb=6486,
  whole270_comb=17680,whole270_deficit_comb=2272,region_target_without_margin=4214,
  core_plus_flow=core+flow,other_region=1832,core_plus_flow_target_if_other_fixed=2382,
  unchanged_core_alone_excess=core-2382,core_states=states,
  new_MAP=False,new_RTL=False,new_SPI_schedule=False,FIT=False,STA=False,P2_selected=False,
  decision='Do not adopt sidecar-only offload with unchanged core. Inline packet references are a bounded next experiment, not an area/timing pass; oversized packets need explicit ownership/continuation.',
  remaining=['Single source/receipt/parser executor with header/map ownership is not implemented.',
   'FPGA must validate reference bounds/types against the consumed command, not trust ARM receipt claims.',
   'Inline requires transport kind/length demultiplexing and a shifted SNES read view; overflow requires two queue slots or a proven split.',
   'New packet CRC/credit/refill/IRQ costs and overlap/polling are not executed.',
   'ARM producer memory is standalone; it is not a full firmware link/stack bound.',
   'Whole RUN/NVIC, active VBlank, CDC/IO/STA and physical deadline remain open.'],
  pins=pins,producer_result_sha256=sha(p/'result.json'),script_sha256=sha(Path(__file__)))
 size=(p/'size.log').read_text().splitlines()[1].split()
 assert list(map(int,size[:3]))==[2032,0,64]
 (d/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps(dict(passed=True,inline_overflow=len(overflow),max_program=max_program,
  warm_extra_ms={k:v['warm_additive_ms_range'] for k,v in summary.items()}),indent=2))

if __name__=='__main__':main()
