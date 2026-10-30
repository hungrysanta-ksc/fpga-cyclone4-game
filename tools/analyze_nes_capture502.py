# SPDX-License-Identifier: MIT
"""502 bounded capture/consumer costs. Separate M4 counts, CPU model and hardware."""
import argparse,json,re
from pathlib import Path
from analyze_nes_capture501 import sha,read
from analyze_nes_status495 import timing
ROOT=Path(__file__).resolve().parents[1]

def inspect(d,baseline,variant='502'):
 r=read(d/'result.json');m=read(d/'inputs.json')
 assert r['completed'] and sha(d/'inputs.json')==r['inputs_SHA256']
 for n,h in m['sources'].items():
  assert sha(d/n)==h
  if n=='planes501_reference.sv':
   assert (d/n).read_text().replace('module planes501_reference(', 'module nes_native_planes165(')==(baseline/'nes_native_planes165.sv').read_text()
  else:
   p=ROOT/f'src/fpga/nes_capture{variant}'/n
   assert sha(p if p.exists()else baseline/n)==h,n
 assert sha(d/'capture500_tb.sv')==m['testbench_SHA256']
 rows=[]
 for c,v in zip(m['cases'],r['results'],strict=True):
  assert c==v['case'];log=d/(c['name']+'.log');assert sha(log)==v['log_SHA256']
  assert (d/(c['name']+'.txt')).read_text()==''.join(' '.join(map(str,x))+'\n'for x in c['events'])
  values={k:int(v,16 if k in ['errors','fetch','compact','raster','patch_errors']else 10)for k,v in(x.split('=')for x in v['summary'].split())}
  eq=re.search(r'EQUIV501 native_rows=(\d+) native_events=(\d+) old_errors=([0-9a-f]+)',log.read_text())
  rows.append(dict(case=c,**values,log_SHA256=sha(log),equivalence=None if not eq else dict(native_rows=int(eq[1]),native_events=int(eq[2]),old_errors=int(eq[3],16))))
 return dict(rows=rows,source_pins=m['sources'],inputs_SHA256=sha(d/'inputs.json'),result_SHA256=sha(d/'result.json'),testbench_SHA256=m['testbench_SHA256'])

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','matrix','boundary','guards','export501','export502','arm','cpu0','cpu1','board','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 matrix=inspect(a.matrix,a.baseline);boundary=inspect(a.boundary,a.baseline);guards=inspect(a.guards,a.baseline)
 normals=matrix['rows']+boundary['rows']
 assert len(matrix['rows'])==27 and len(boundary['rows'])==6 and len(guards['rows'])==12
 assert all(x['valid']==1 and x['errors']==0 and x['exact_pixels']==x['patches']*256 and x['equivalence']['native_rows']==224-x['patches']for x in normals)
 assert next(x for x in normals if x['case']['name']=='four-raw-rows')['patches']==4
 assert all(x['valid']==0 for x in guards['rows'])
 old=read(ROOT/'analysis/capture501-verification.json');pairs=[]
 for before,after in zip(old['matrix']['rows'],matrix['rows'],strict=True):
  assert before['case']==after['case']
  pairs.append(dict(case=after['case']['name'],raw501=before['patches'],raw502=after['patches']))
 exports={v:inspect(getattr(a,'export'+v),a.baseline,v)for v in ['501','502']}
 arm=read(a.arm/'result.json');cpu=[read(a.cpu0/'result.json'),read(a.cpu1/'result.json')]
 assert arm['passed'] and all(c['passed']and c['pixels_equal']for c in cpu)
 pins=read(a.board/'source-pins.json')
 assert pins['baseline_inputs']==read(ROOT/'analysis/boot493-verification.json')['FPGA']['source_inputs']
 for n,h in pins['board_inputs'].items():assert sha(a.board/n)==h
 for n in ['nes_native_planes165.sv','nes_native_frame201.sv']:assert pins['board_inputs'][n]==matrix['source_pins'][n]
 summary=(a.board/'output_files/board.fit.summary').read_text();assert 'Fitter Status : Successful' in summary
 def val(label):return int(re.search(re.escape(label)+r' : ([\d,]+)',summary)[1].replace(',',''))
 cost=dict(LE=val('Total logic elements'),comb=val('Total combinational functions'),FF=val('Dedicated logic registers'),RAM_bits=val('Total memory bits'))
 rpt=a.board/'output_files/board.fit.rpt';cost['M9K']=int(re.search(r'; M9Ks\s*; (\d+) /',rpt.read_text(errors='replace'))[1])
 cost['delta_vs501']={k:v-old['FPGA'][k]for k,v in cost.items()}
 cost['remaining_LE']=15408-cost['LE'];cost['related_timing_ns']=timing(a.board)
 cost['whole_board_inputs']=pins['board_inputs'];cost['report_SHA256']={p.name:sha(p)for p in [rpt,a.board/'output_files/board.fit.summary',a.board/'output_files/board.sta.rpt',a.board/'implementation-paths204.tsv',a.board/'nominal-paths204.tsv']}
 rows=arm['rows'];diff={}
 for k in ['receive_instructions','planner_instructions']:diff[k]=rows[1]['ARM'][k]-rows[0]['ARM'][k]
 for k in ['E1_wire_B','target_instructions']:diff[k]=rows[1]['serializer'][k]-rows[0]['serializer'][k]
 diff['source_SPI_wire_B']=sum(rows[1]['source_SPI_wire_B'].values())-sum(rows[0]['source_SPI_wire_B'].values())
 for c in cpu:
  c['delta_masterclocks']={k:c['rows'][1]['frames'][0][k]-c['rows'][0]['frames'][0][k]for k in ['ACK_masterclock','final_ready_masterclock','decode_masterclocks']}
 result=dict(experiment=502,physical_baseline='MMC493',new_installer=False,production_selected=False,new_physical_FPS=None,A1_complete=False,bounded_capture_consumer_gate_passed=True,
  matrix=matrix,boundary=boundary,guards=guards,paired=pairs,reduced_raw_rows=sum(x['raw501']-x['raw502']for x in pairs),raw_pixel_comparisons=sum(x['exact_pixels']for x in normals),native_event_comparisons=sum(x['equivalence']['native_events']for x in normals),exports=exports,ARM=arm,ARM_delta=diff,SNES=cpu,FPGA=cost,
  new_ARM_Flash_B=0,new_ARM_static_RAM_B=0,full_end_to_end_frame_ms=None,
  limits=['Deterministic always-ready VRAM and empty OAM,not game CPU/MMC3/PSRAM/IRQ competition','One cold fixed PPU scene through actual source/M4/65816;source release and transport/ACK endpoints modeled','M4 instruction counts and65816 modeled clocks are separate,no additive full RUN bound','Four admission credits and2.625Mbps E1 byte clock;not current shared SPI/refill/IRQ/ROM arbitration','Related STA only;full reset/CDC/IO and physical STOP/menu/FPS remain493 evidence'],
  next='Prepare uniquely named limited502 trial with unchanged493 ARM/SNES behavior and restore path;verify capture/display intervals in matched gameplay,then carry real shared SPI/IRQ/ROM costs into A2. Do not repeat unchanged bounded tests/FIT or resume frozen status/FSM work.',
  excluded=[dict(run='export501-01',reason='Testbench producer instantiated before wire declarations;implicit nets caused9 compile errors. Fixed declaration order only;both export02 runs pass. Product RTL unchanged.'),dict(run='boundary01/export502-01',reason='Prepared only;superseded before execution,not PASS evidence')],
  evidence_SHA256={str(d):sha(d/'result.json')for d in [a.arm,a.cpu0,a.cpu1]},
  sources={str(p.relative_to(ROOT)).replace(chr(92),'/'):sha(p)for p in list((ROOT/'src/fpga/nes_capture502').glob('*.sv'))+list((ROOT/'tools').glob('*capture502*.py'))})
 a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(raw_reduction=result['reduced_raw_rows'],ARM_delta=diff,LE=cost['LE'],cpu=[c['delta_masterclocks']for c in cpu])))
