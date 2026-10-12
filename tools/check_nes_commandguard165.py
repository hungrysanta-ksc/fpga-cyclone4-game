# SPDX-License-Identifier: MIT
"""Bind state-command factoring, loader equivalence, reused SPI and timing."""
from pathlib import Path
import argparse,csv,json,re
from nes_game147 import ROOT,sha
from nes_commandguard165 import transform
from test_nes_state165 import bench
from nes_release165 import TARGETS
from check_nes_check165 import inspect
from check_nes_retire165 import nominal

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','reproduced','test']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();d=a.candidate;m=json.loads((d/'preparation.json').read_bytes());b=json.loads((a.baseline/'result.json').read_bytes())
 assert sha(a.baseline/'result.json')==m['baseline_result_sha256'] and m==json.loads((a.reproduced/'preparation.json').read_bytes())
 assert len(m['sources'])==61 and m['changed']==['nes_rom_loader.sv']
 for n,h in m['sources'].items():
  assert sha(d/n)==sha(a.reproduced/n)==h,n
  assert sha(a.baseline/n)==m['baseline'][n],n
  if n!='nes_rom_loader.sv':assert h==m['baseline'][n],n
 assert (d/'nes_rom_loader.sv').read_text()==transform((a.baseline/'nes_rom_loader.sv').read_text())
 t=json.loads((a.test/'result.json').read_bytes())
 assert t['passed'] and t['states']==294912 and t['sequences']==1056 and t['wrong_stop_rejected']
 assert sha(d/'nes_rom_loader.sv')==t['source_sha256']==sha(a.test/'candidate.sv')
 assert sha(a.baseline/'nes_rom_loader.sv')==t['reference_sha256']
 assert (a.test/'state165_tb.sv').read_text()==bench()
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
 for stem in ['length165','release165','commandguard165']:assert sha(d/(stem+'-paths.tcl'))==sha(ROOT/'tools'/('nes_'+stem+'_paths.tcl'))
 public={**b['public_sources'],**m['public_sources'],**t['public_sources'],'tools/check_nes_commandguard165.py':sha(Path(__file__)),'tools/nes_length165_paths.tcl':sha(ROOT/'tools/nes_length165_paths.tcl'),'tools/nes_commandguard165_paths.tcl':sha(ROOT/'tools/nes_commandguard165_paths.tcl')}
 public=canonical_pins(public)
 for n,h in public.items():assert sha(ROOT/n)==h,n
 result={**inspect(d),'nominal':nominal(d),'baseline_nominal':nominal(a.baseline),'functional_test':t,'spi_functional_test':b['spi_functional_test'],
 'length_to_clear_setup_ns':min(float(r['slack']) for r in target),'release_to_held_setup_ns':min(float(r['slack']) for r in chains if r['group']=='held'),
 'local_release_chain_setup_hold_pass':True,'source_byte_reproduction':True,'unchanged_files':60,'unchanged_from_phaseguard165':59,'stop_to_state_setup_ns':min(float(r['slack']) for r in rows('commandguard165-paths.tsv')),
 'keep_assignment_nodes':keep_nodes,'keep_assignment_readback':True,'target_path_logic_levels':logic_levels,
 'functional_reuse':'New loader all-state and sequential comparison. SPI numeric-keep source byte-identical to map02; previous normalized SPI capture/connected evidence reused. No new full composition/game run.',
 'scope':'State-specific IDLE/READY/RECEIVE/RUN illegal command factoring; original error/data/timer unchanged. Balanced numeric-keep comparator retained. New fit, path reports and local release chains; IO/CDC/MCU remains open.',
 'cartridge_sram_reserved':True,'hardware_package':False,'public_sources':public}
 assert not (d/'result.json').exists();(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['fit_le','used_labs','nominal','length_to_clear_setup_ns','stop_to_state_setup_ns','release_to_held_setup_ns']}))
if __name__=='__main__':main()
