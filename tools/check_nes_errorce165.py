# SPDX-License-Identifier: MIT
"""Bind combined counter/loader candidate, new loader error-code equivalence and connected replay."""
from pathlib import Path
import argparse,csv,json,re
from nes_game147 import ROOT,sha
from nes_errorce165 import transform
from test_nes_retirece165 import bench,connected
from nes_release165 import TARGETS
from check_nes_check165 import inspect
from check_nes_retire165 import nominal

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','reproduced','test','connected','loader-test']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();d=a.candidate;m=json.loads((d/'preparation.json').read_bytes());b=json.loads((a.baseline/'result.json').read_bytes())
 assert sha(a.baseline/'result.json')==m['baseline_result_sha256'] and m==json.loads((a.reproduced/'preparation.json').read_bytes())
 assert len(m['sources'])==61 and m['changed']==['nes_rom_loader.sv']
 for n,h in m['sources'].items():
  assert sha(d/n)==sha(a.reproduced/n)==h,n
  assert sha(a.baseline/n)==m['baseline'][n],n
  if n!='nes_rom_loader.sv':assert h==m['baseline'][n],n
 assert (d/'nes_rom_loader.sv').read_text()==transform((a.baseline/'nes_rom_loader.sv').read_text())
 t=json.loads((a.test/'result.json').read_bytes())
 assert t['passed'] and t['states']==786432 and t['captures']==393741 and t['wrong_fault_gate_rejected']
 assert sha(d/'nes_rom_spi.sv')==sha(a.test/'candidate.sv')==t['source_sha256']
 assert b['spi_functional_test']==t
 assert (a.test/'capture_tb.sv').read_text()==bench() and (a.test/'tag165_tb.sv').read_text()==connected()
 for n in ['nes_rom_boot.sv','nes_rom_physical.sv']:assert sha(d/n)==sha(a.test/n)
 lt=json.loads((a.loader_test/'result.json').read_bytes())
 assert lt['passed'] and lt['states']==294912 and lt['sequences']==1056 and lt['wrong_stop_rejected'] and lt['wrong_error_code_rejected']
 assert sha(d/'nes_rom_loader.sv')==lt['source_sha256'] and sha(a.baseline/'nes_rom_loader.sv')==lt['reference_sha256']
 joint=json.loads((a.connected/'result.json').read_bytes());assert joint['passed']
 for n,h in joint['sources'].items():assert sha(d/n)==sha(a.connected/n)==h,n
 assert joint['reference_sha256']==t['reference_sha256'] and joint['bench_sha256']==sha(a.connected/'tag165_tb.sv')
 assert (a.connected/'tag165_tb.sv').read_text()==connected()
 def rows(n):return list(csv.DictReader((d/n).open(),delimiter='\t'))
 paths=rows('retirece165-paths.tsv');assert len(paths)==18
 assert {r['target']:r['value'] for r in rows('release165-settings.tsv')}==dict.fromkeys(TARGETS,'ON')
 topology=rows('release165-topology.tsv');chains=rows('release165-paths.tsv');assert len(chains)==15
 for name in ['records','prepared']:
  first=[r for r in topology if r['chain']==name and r['stage']=='0'];assert len(first)==1 and first[0]['to']==first[0]['from'][:-2]+'1]'
 assert all(float(r['slack'])>=0 for r in chains if r['group']!='held')
 mapping=(d/'output_files/board.map.rpt').read_text()
 for node in [f'length_pair_equal[{i}]' for i in range(11)]+[f'length_group_equal[{i}]' for i in range(3)]:
  for option in ['IGNORE_LCELL_BUFFERS','REMOVE_REDUNDANT_LOGIC_CELLS']:
   assert re.search(re.escape(option)+r'\s*;\s*off\s*;\s*-\s*;\s*'+re.escape(node)+r'\s*;',mapping),(node,option)
 for i in range(19):
  assert re.search(r'AUTO_CLOCK_ENABLE_RECOGNITION\s*;\s*ON\s*;\s*-\s*;\s*'+re.escape(f'check_next[{i}]')+r'\s*;',mapping)
 explicit_ce_hint_reported=bool(re.search(r'IMPLEMENT_AS_CLOCK_ENABLE\s*;\s*on\s*;\s*-\s*;\s*counter_update_enable\s*;',mapping,re.I))
 ena=set()
 for f in d.glob('retirece165-*-failure-setup.rpt'):
  ena.update(re.findall(r'check_next\[(\d+)\]\|ena',f.read_text()))
 assert ena=={str(i) for i in range(19)},('routed enable endpoints',ena)
 public={**b['public_sources'],**m['public_sources'],**t['public_sources'],**lt['public_sources'],**joint['public_sources'],'tools/check_nes_errorce165.py':sha(Path(__file__))}
 for stem in ['release165','retirece165','errorce165']:
  n='tools/nes_'+stem+'_paths.tcl';assert sha(d/(stem+'-paths.tcl'))==sha(ROOT/n);public[n]=sha(ROOT/n)
 for n,h in public.items():assert sha(ROOT/n)==h,n
 error_paths=rows('errorce165-paths.tsv');assert len(error_paths)==6
 result={**inspect(d),'nominal':nominal(d),'baseline_nominal':nominal(a.baseline),'functional_test':lt,'combined_spi_test':joint,'spi_functional_test':t,'state_to_error_ns':{kind:min(float(r['slack']) for r in error_paths if r['kind']==kind) for kind in ['setup','hold']},
 'targeted_ns':{group:{kind:min(float(r['slack']) for r in paths if r['group']==group and r['kind']==kind) for kind in ['setup','hold']} for group in ['failure','length','stop']},
 'release_to_held_setup_ns':min(float(r['slack']) for r in chains if r['group']=='held'),'local_release_chain_setup_hold_pass':True,'routed_counter_enable_bits':sorted(map(int,ena)),
 'source_byte_reproduction':True,'unchanged_files':60,'unchanged_from_phaseguard165':59,'clock_latency_changed':False,'cartridge_sram_reserved':True,'hardware_package':False,'auto_enable_assignment_bits':19,'explicit_ce_hint_reported':explicit_ce_hint_reported,
 'scope':'Dedicated CHECK update enable plus numeric-keep live length equality and state-specific loader command factoring plus separate error code owner. Same retirement fault/response priority; new error-event/code owner equivalence and combined SPI replay. Counter/capture and actual SPI/boot/READ16 tested, seeded READY/count; no full ROM/game/MCU/SNES replay. Full IO/CDC/reset signoff remains open.','public_sources':public}
 assert not (d/'result.json').exists();(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['fit_le','used_labs','nominal','targeted_ns','routed_counter_enable_bits']}))
if __name__=='__main__':main()
