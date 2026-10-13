# SPDX-License-Identifier: MIT
"""Record actual area-mode application, source reuse, and resource failure."""
from pathlib import Path
import argparse,json,re
from nes_game147 import ROOT,sha
from nes_oam_select165 import transform

def inspect(baseline,candidate,reproduced,tests):
 meta=json.loads((candidate/'preparation.json').read_bytes())
 rep=json.loads((reproduced/'preparation.json').read_bytes())
 assert meta['changed']==rep['changed']==['board.qsf']
 assert meta['sources']==rep['sources'] and meta['baseline']==rep['baseline']
 for n,h in meta['sources'].items():
  assert sha(candidate/n)==sha(reproduced/n)==h,n
  assert sha(baseline/n)==meta['baseline'][n],n
  if n!='board.qsf':assert h==meta['baseline'][n],n
 assert (candidate/'board.qsf').read_text()==(baseline/'board.qsf').read_text()+'\nset_global_assignment -name CYCLONEII_OPTIMIZATION_TECHNIQUE AREA\n'
 for n,h in rep['public_sources'].items():assert sha(ROOT/n)==h,n
 report=(candidate/'output_files/board.map.rpt').read_text(errors='replace')
 log=(candidate/'map.log').read_text(errors='replace');fit=(candidate/'fit.log').read_text(errors='replace')
 assert 'Analysis & Synthesis was successful' in log
 assert re.search(r'; Optimization Technique\s*; Area\s*;',report)
 def value(label):
  m=re.search(r'^; '+re.escape(label)+r'\s*; ([\d,]+)',report,re.M);assert m,label
  return int(m[1].replace(',',''))
 resources={n:value(label) for n,label in [('estimated_le','Estimated Total logic elements'),('combinational','Total combinational functions'),('registers','Total registers'),('memory_bits','Total memory bits'),('pins','Total pins'),('virtual_pins','Total virtual pins')]}
 prior=json.loads((baseline/'result.json').read_bytes())['resources']
 assert resources['combinational']<prior['combinational']
 errors=re.findall(r'^Error \(\d+\):.*',fit,re.M)
 assert any('Error (170011)' in s for s in errors) and any('Error (171000)' in s for s in errors)
 cases=[]
 for directory,variant in zip(tests,['onehot-read','row-writer']):
  t=json.loads((directory/'result.json').read_bytes());assert t['passed']
  assert t['reference_sha256']==sha(baseline/'rtl/ppu.sv')
  expected=transform((baseline/'rtl/ppu.sv').read_text(),variant)
  actual=(directory/'oam_banked.sv').read_text()
  m=re.search(r'(?ms)^module OAMEval\(.*?^endmodule',expected);assert m
  assert m[0].replace('module OAMEval(','module oam_banked(',1) in actual
  cases.append(dict(variant=variant,passed=True,adopted=False,**{n:t[n] for n in ['cycles','row_copies','cpu_writes','savestate_writes','write_collisions','source_sha256']}))
 result=dict(synthesis_pass=True,fit_pass=False,selected='area',rtl_changed=False,cartridge_sram_reserved=True,resources=resources,baseline_resources=prior,
  combinational_reduction=prior['combinational']-resources['combinational'],device_limit=15408,combinational_excess=resources['combinational']-15408,
  fit_errors=errors,rejected_variants=cases,source_byte_reproduction=True,unchanged_files=len(meta['sources'])-1,
  functional_reuse='Exact board03 RTL/SDC/ROM bytes: reuse sink-board165 test04; no new game boot or board simulation for area-only settings.',
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_oam_select165.py','tools/test_nes_oam_select165.py','tools/check_nes_oam_select165.py','tests/nes-functional/oam_banked_tb.sv']},
  raw_sha256={n:sha(candidate/n) for n in ['map.log','fit.log','output_files/board.map.rpt','output_files/board.fit.rpt','preparation.json']},
  whole_firmware_link=False,hardware_package=False,timing_approved=False)
 assert not (candidate/'result.json').exists(),'Do not overwrite completed evidence'
 (candidate/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','reproduced']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--tests',type=Path,nargs=2,required=True);a=p.parse_args()
 r=inspect(a.baseline,a.candidate,a.reproduced,a.tests)
 print(json.dumps({n:r[n] for n in ['synthesis_pass','fit_pass','resources','combinational_reduction','combinational_excess','unchanged_files']}))
