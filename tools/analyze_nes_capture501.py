# SPDX-License-Identifier: MIT
"""501 bounded capture correction ledger; no installer or physical FPS inference."""
import argparse,json,re,hashlib
from pathlib import Path
from analyze_nes_status495 import timing
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
def inspect(path,board):
 r=read(path/'result.json');m=read(path/'inputs.json');assert r['completed'] and sha(path/'inputs.json')==r['inputs_SHA256']
 for n,h in m['sources'].items():
  assert sha(path/n)==h,n
  if n=='planes501_reference.sv':
   assert (path/n).read_text().replace('module planes501_reference(', 'module nes_native_planes165(')==(board/'nes_native_planes165.sv').read_text()
  else:
   p=ROOT/'src/fpga/nes_capture501'/n
   assert h==sha(p if p.exists() else board/n),n
 assert sha(path/'capture500_tb.sv')==m['testbench_SHA256']
 rows=[]
 for c,v in zip(m['cases'],r['results'],strict=True):
  assert c==v['case'];log=path/(c['name']+'.log');assert sha(log)==v['log_SHA256']
  assert (path/(c['name']+'.txt')).read_text()==''.join(' '.join(map(str,x))+'\n'for x in c['events'])
  d={k:int(v,16 if k in ['errors','fetch','compact','raster','patch_errors'] else 10)for k,v in (x.split('=')for x in v['summary'].split())}
  eq=re.search(r'EQUIV501 native_rows=(\d+) native_events=(\d+) old_errors=([0-9a-f]+)',log.read_text())
  rows.append(dict(case=c,**d,log_SHA256=sha(log),equivalence=None if not eq else dict(native_rows=int(eq[1]),native_events=int(eq[2]),old_errors=int(eq[3],16))))
 return dict(rows=rows,source_pins=m['sources'],inputs_SHA256=sha(path/'inputs.json'),result_SHA256=sha(path/'result.json'),testbench_SHA256=m['testbench_SHA256'])
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','matrix','guards','board','previous-matrix','previous-board','arm','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 matrix=inspect(a.matrix,a.baseline);guards=inspect(a.guards,a.baseline)
 assert len(matrix['rows'])==27 and all(x['valid']==1 and x['fetch']==0 and x['exact_pixels']==x['patches']*256 for x in matrix['rows'])
 names={1:'physical CHR region',2:'ROM DATA invalid',3:'physical/logical byte lane',4:'asynchronous ROM fault',5:'missing pixel',6:'wrong row identity',7:'missing raw receipt',8:'wrong raw generation',9:'raw capacity overflow',10:'STOP plus early query',11:'missing native high outside transition',12:'physical/logical plane lane'}
 for row in guards['rows']:row['fault_name']=names[row['case']['guard']]
 selected_guards=guards['rows'];assert len(selected_guards)==12 and all(x['valid']==0 for x in selected_guards)
 assert all(x['equivalence']['native_rows']==224-x['patches'] for x in matrix['rows'])
 old=read(ROOT/'analysis/capture500-verification.json');oldrows=old['matrix']['rows']+old['phase']['rows'];paired=[]
 for before in oldrows:
  after=next(x for x in matrix['rows']if x['case']['name']==before['case']['name'])
  assert before['case']==after['case']
  paired.append(dict(case=before['case']['name'],before_valid=before['valid'],after_valid=after['valid'],before_fetch=before['fetch'],before_raw_rows=before['patches'],after_raw_rows=after['patches']))
 pins=read(a.board/'source-pins.json');basepins=read(ROOT/'analysis/boot493-verification.json')['FPGA']['source_inputs'];assert pins['baseline_inputs']==basepins
 for n,h in pins['board_inputs'].items():assert sha(a.board/n)==h
 for n in ['nes_native_planes165.sv','nes_native_frame201.sv']:assert pins['board_inputs'][n]==matrix['source_pins'][n]
 summary=(a.board/'output_files/board.fit.summary').read_text();fit='Fitter Status : Successful' in summary
 def val(label):
  m=re.search(re.escape(label)+r' : ([\d,]+)',summary);return int(m[1].replace(',',''))if m else None
 cost=dict(fit_passed=fit,LE=val('Total logic elements'),comb=val('Total combinational functions'),FF=val('Dedicated logic registers'),RAM_bits=val('Total memory bits'))
 rpt=a.board/'output_files/board.fit.rpt';mr=re.search(r'; M9Ks\s*; (\d+) /',rpt.read_text(errors='replace'));cost['M9K']=int(mr[1]) if mr else None
 cost['related_timing_ns']=timing(a.board) if (a.board/'implementation-paths204.tsv').exists() else None
 cost['baseline']=dict(LE=15272,comb=14078,FF=8392,RAM_bits=264800,M9K=51)
 cost['delta']={k:None if cost[k] is None else cost[k]-v for k,v in cost['baseline'].items()}
 cost['remaining_LE']=None if cost['LE'] is None else 15408-cost['LE'];cost['whole_board_inputs']=pins['board_inputs'];cost['report_SHA256']={p.name:sha(p)for p in [rpt,a.board/'output_files/board.fit.summary',a.board/'output_files/board.sta.rpt']if p.exists()}
 previous=read(a.previous_matrix/'result.json');previous_pins=read(a.previous_board/'source-pins.json');previous_inputs=read(a.previous_matrix/'inputs.json')
 assert previous_inputs['sources']['nes_native_planes165.sv']==previous_pins['board_inputs']['nes_native_planes165.sv']
 rejected=[x['case']['name']for x in previous['results']if x['summary'].startswith('valid=0 ')]
 assert rejected==['f699-addr0-d1','f699-addr1-d1'],rejected
 sink=a.arm/'nes_native_sink165.c';sink_text=sink.read_text();audit=read(ROOT/'analysis/audit499-verification.json')
 known=next(x for x in audit['ARM_NES_inventory']if x['path']=='nes_native_sink165.c');assert sha(sink)==known['SHA256']
 assert 'unsigned packed=2048' in sink_text and 'if(p->patch_count<=2)' in sink_text and 'for(unsigned plane=0;plane<3;plane++)' in sink_text
 raw_cost=dict(source_SHA256=sha(sink),method='Static audit of actual493 serializer;not executed ARM cycle/SPI measurement',CHR_bytes_before_span_RLE={str(n):(3*n*32*2 if n<=2 else 2048)for n in [1,2,3]},extra_row_crosses_compact_threshold=True,actual_wire_delta_B=None,actual_time_delta_ms=None)
 result=dict(experiment=501,physical_baseline='MMC493',new_installer=False,new_physical_FPS=None,production_selected=False,A1_complete=False,
  matrix=matrix,guards=guards,paired=paired,recovered_old_conditions=sum(not x['before_valid'] and x['after_valid']for x in paired),
  raw_pixel_comparisons=sum(x['exact_pixels']for x in matrix['rows']),native_event_comparisons=sum(x['equivalence']['native_events']for x in matrix['rows']),FPGA=cost,ARM_SNES_program_unchanged=True,new_ARM_Flash_B=0,new_ARM_static_RAM_B=0,ARM_raw_threshold=raw_cost,
  full_end_to_end_frame_ms=None,wire_delta_B=None,
  intermediate=dict(matrix='test03',board='board01',rejected_conditions=rejected,reason='Valid logical/physical low-plane address at high-load after restart was still rejected;raw rows now validate bus lanes independently of load naming',whole_inputs=previous_pins['board_inputs']),
  excluded=[dict(run='guards02/guard11',reason='High suppression targeted193:16 after render-off193:7;no event was removed;expected rejection failed. guards03 moves to192:16 and asserts exactly one real high was removed.')],
  limits=['Actual PPU with deterministic always-ready VRAM,not CPU/MMC3/PSRAM/game/IRQ contention','Raw pixels match same PPU post-CE observer;native events compared exactly outside patched rows in27 cases;not independent emulator/full SNES image','Empty OAM fixture;OBJ pair faults remain strict;not every physical fetch episode proven','Current/next row fallback may add256 raw pixels and cross actual493 compact-raw threshold from384 to2048 CHR bytes before span RLE;SPI bytes and time not measured','Full reset/CDC/IO signoff and physical STOP/menu/FPS remain unchanged493 evidence'],
  next='Keep A1 open:avoid unnecessary third raw row or account for493 compact/full CHR threshold,then bind real source/ARM/planner/65816 raw consumption and physical rejection/display intervals. No blind error masking,seed loops or498 promotion.',
  sources={str(p.relative_to(ROOT)).replace(chr(92),'/'):sha(p)for p in list((ROOT/'src/fpga/nes_capture501').glob('*.sv'))+list((ROOT/'tools').glob('*capture501*.py'))})
 a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({k:result[k]for k in ['recovered_old_conditions','raw_pixel_comparisons','A1_complete']}));print(json.dumps(cost['delta']))
