# SPDX-License-Identifier: MIT
"""Bind STOP operand capture, connected SPI regression, reproduction and timing."""
from pathlib import Path
import argparse,csv,json,re
from nes_game147 import ROOT,sha
from nes_lengthkeep165 import transform
from test_nes_balancedlength165 import bench,connected
from nes_release165 import TARGETS
from check_nes_check165 import inspect
from check_nes_retire165 import nominal

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','reproduced','test']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();d=a.candidate;m=json.loads((d/'preparation.json').read_bytes());b=json.loads((a.baseline/'result.json').read_bytes())
 assert sha(a.baseline/'result.json')==m['baseline_result_sha256'] and m==json.loads((a.reproduced/'preparation.json').read_bytes())
 assert len(m['sources'])==61 and m['changed']==['nes_rom_spi.sv']
 for n,h in m['sources'].items():
  assert sha(d/n)==sha(a.reproduced/n)==h,n
  assert sha(a.baseline/n)==m['baseline'][n],n
  if n!='nes_rom_spi.sv':assert h==m['baseline'][n],n
 assert (d/'nes_rom_spi.sv').read_text()==transform((a.baseline/'nes_rom_spi.sv').read_text())
 t=json.loads((a.test/'result.json').read_bytes())
 assert t['passed'] and t['captures']==393741 and t['wrong_offset_rejected'] and t['retirement_live_length_changed']
 actual=(d/'nes_rom_spi.sv').read_text();executed=(a.test/'candidate.sv').read_text()
 assert actual.count('(* keep = 1 *)')==2
 assert actual.replace('(* keep = 1 *)','(* keep = "true" *)')==executed
 assert sha(a.test/'candidate.sv')==t['source_sha256']
 assert sha(a.baseline/'nes_rom_spi.sv')==t['reference_sha256']
 assert (a.test/'capture_tb.sv').read_text()==bench() and (a.test/'tag165_tb.sv').read_text()==connected()
 for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:assert sha(d/n)==sha(a.test/n)
 def rows(n):return list(csv.DictReader((d/n).open(),delimiter='\t'))
 target=rows('length165-paths.tsv');assert len(target)==3
 mapping=(d/'output_files/board.map.rpt').read_text()
 keep_nodes=[f'length_pair_equal[{i}]' for i in range(11)]+[f'length_group_equal[{i}]' for i in range(3)]
 for node in keep_nodes:
  for option in ['IGNORE_LCELL_BUFFERS','REMOVE_REDUNDANT_LOGIC_CELLS']:
   assert re.search(re.escape(option)+r'\s*;\s*off\s*;\s*-\s*;\s*'+re.escape(node)+r'\s*;',mapping),(node,option)
 logic_levels=[]
 for i in range(3):
  path=(d/f'length165-{i}-clear.rpt').read_text()
  assert 'length_pair_equal' in path and 'length_group_equal' in path
  logic_levels.append(int(re.search(r'Number of Logic Levels\s*;\s*;\s*(\d+)',path)[1]))
 assert {r['target']:r['value'] for r in rows('release165-settings.tsv')}==dict.fromkeys(TARGETS,'ON')
 topology=rows('release165-topology.tsv');chains=rows('release165-paths.tsv');assert len(chains)==15
 for name in ['records','prepared']:
  first=[r for r in topology if r['chain']==name and r['stage']=='0'];assert len(first)==1 and first[0]['to']==first[0]['from'][:-2]+'1]'
 assert all(float(r['slack'])>=0 for r in chains if r['group']!='held')
 for stem in ['length165','release165']:assert sha(d/(stem+'-paths.tcl'))==sha(ROOT/'tools'/('nes_'+stem+'_paths.tcl'))
 public={**b['public_sources'],**m['public_sources'],**t['public_sources'],'tools/check_nes_lengthkeep165.py':sha(Path(__file__)),'tools/nes_length165_paths.tcl':sha(ROOT/'tools/nes_length165_paths.tcl')}
 public=canonical_pins(public)
 for n,h in public.items():assert sha(ROOT/n)==h,n
 result={**inspect(d),'nominal':nominal(d),'baseline_nominal':nominal(a.baseline),'functional_test':b['functional_test'],'spi_functional_test':t,
 'length_to_clear_setup_ns':min(float(r['slack']) for r in target),'release_to_held_setup_ns':min(float(r['slack']) for r in chains if r['group']=='held'),
 'local_release_chain_setup_hold_pass':True,'source_byte_reproduction':True,'unchanged_files':60,'unchanged_from_state165':59,
 'keep_assignment_nodes':keep_nodes,'keep_assignment_readback':True,'target_path_logic_levels':logic_levels,
 'functional_reuse':'Only two keep attributes true-string -> numeric1; normalized executed RTL byte-text identical, test source hashes retained. No new Questa run.','scope':'Balanced live offset/length equality with preserved combinational boundaries; no added register or latency. Actual connected SPI/boot/READ16 regression with seeded loader READY/count, not full-ROM loading, game or MCU/SNES test. Loader phaseguard equivalence reused byte-exact. External IO/CDC/reset remains open.',
 'cartridge_sram_reserved':True,'hardware_package':False,'public_sources':public}
 assert not (d/'result.json').exists();(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['fit_le','used_labs','nominal','length_to_clear_setup_ns','release_to_held_setup_ns']}))
if __name__=='__main__':main()
