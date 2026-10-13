# SPDX-License-Identifier: MIT
"""Exact predecode materialization, capture/retirement proof and whole-fit evidence."""
from pathlib import Path
import argparse,csv,json
from nes_game147 import ROOT,sha
from nes_predecode165 import transform,specialize,masked,loader
from test_nes_predecode165 import bench
from check_nes_check165 import inspect
from check_nes_retire165 import nominal

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','reproduced','test','path-test','length-test','first','second']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--third',type=Path)
 a=p.parse_args();m=json.loads((a.candidate/'preparation.json').read_bytes());rep=json.loads((a.reproduced/'preparation.json').read_bytes())
 assert m['sources']==rep['sources'] and m['baseline']==rep['baseline'] and m['variant']==rep['variant']
 assert m['changed']==['nes_rom_loader.sv','nes_rom_spi.sv'] and len(m['sources'])==61
 for n,h in rep['public_sources'].items():assert sha(ROOT/n)==h,n
 for n,h in m['sources'].items():
  assert sha(a.candidate/n)==sha(a.reproduced/n)==h,n
  assert sha(a.baseline/n)==m['baseline'][n],n
  if n not in m['changed']:assert h==m['baseline'][n],n
 expected=specialize(transform((a.baseline/'nes_rom_spi.sv').read_text()))
 if m['variant']=='masked':expected=masked(expected)
 else:assert m['variant']=='specialized'
 assert (a.candidate/'nes_rom_spi.sv').read_text()==expected
 assert (a.candidate/'nes_rom_loader.sv').read_text()==loader((a.baseline/'nes_rom_loader.sv').read_text())
 t=json.loads((a.test/'result.json').read_bytes());s=json.loads((a.path_test/'result.json').read_bytes())
 assert t['passed'] and t['states']==786432 and t['captures']==393216
 assert t['wrong_fault_gate_rejected'] and t['wrong_header_gate_rejected']
 assert t['reference_sha256']==sha(a.baseline/'nes_rom_spi.sv')
 assert t['source_sha256']==sha(a.test/'candidate.sv')==sha(a.candidate/'nes_rom_spi.sv')
 assert (a.test/'check165_tb.sv').read_text()==bench()
 assert s['passed'] and s['expected_reply_id']=='6B' and s['derived_length_flag_seeded_with_count']
 l=json.loads((a.length_test/'result.json').read_bytes())
 assert l['passed'] and l['states']==628736 and l['wrong_terminal_count_rejected']
 assert l['source_sha256']==sha(a.candidate/'nes_rom_loader.sv')==sha(a.length_test/'candidate.sv')
 assert l['reference_sha256']==sha(a.baseline/'nes_rom_loader.sv')
 for n,h in s['sources'].items():
  assert sha(a.path_test/'path'/n)==h,n
  if n!='game147_path_tb.sv':assert sha(a.candidate/n)==h,n
 assert sha(a.candidate/'secondary165-timing.tcl')==sha(ROOT/'tools/nes_secondary165_timing.tcl')
 targets={}
 trials=[a.first,a.second]+([a.third] if a.third else [])
 for d in trials+[a.candidate]:
  assert sha(d/'board.sdc')==sha(a.baseline/'board.sdc')
  assert sha(d/'predecode165-paths.tcl')==sha(ROOT/'tools/nes_predecode165_paths.tcl')
  rows=list(csv.DictReader((d/'predecode165-paths.tsv').open(),delimiter='\t'));assert len(rows)==9
  targets[d.name]={g:min(float(r['slack']) for r in rows if r['group']==g) for g in ['counter','capture','address']}
 public=['tools/nes_predecode165.py','tools/test_nes_predecode165.py','tools/test_nes_length165.py','tools/test_nes_predecode_path165.py','tools/nes_predecode165_paths.tcl','tools/check_nes_predecode165.py','tools/test_nes_check165.py','tools/test_nes_check_path165.py','tools/test_nes_game149_spi.py','tests/nes-functional/game147_path_tb.sv','tests/nes-functional/counter131_diff_tb.sv','tools/check_nes_check165.py','tools/check_nes_oam_port165.py','tools/check_nes_retire165.py','tools/check_nes_retire165_nominal.py','tools/nes_secondary165_timing.tcl']
 result={**inspect(a.candidate),'nominal':nominal(a.candidate),'functional_states':786432,'capture_cases':393216,'loader_cases':628736,'wrong_fault_gate_rejected':True,'wrong_header_gate_rejected':True,'wrong_terminal_count_rejected':True,
  'prior_candidates':{d.name:{**inspect(d),'nominal':nominal(d)} for d in trials},'targeted_nominal_setup_ns':targets,
  'spi_summary':s['summary'],'unchanged_files':59,'clock_latency_changed':False,'source_byte_reproduction':True,'implementation_sdc_unchanged':True,
  'cartridge_sram_reserved':True,'whole_firmware_link':False,'hardware_package':False,
  'scope':'Predecode static command validity at original frame capture; dynamic faults/response ownership still gate original retirement edge. Captured predicates compared to prior encoded fields. No new full game boot or IO/CDC signoff.',
  'public_sources':{n:sha(ROOT/n) for n in public}}
 assert not (a.candidate/'result.json').exists()
 (a.candidate/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
