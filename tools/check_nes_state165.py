# SPDX-License-Identifier: MIT
"""Bind independent loader state equations to differential test and full fit."""
from pathlib import Path
import argparse,csv,json
from nes_game147 import ROOT,sha
from nes_state165 import transform
from test_nes_state165 import bench
from nes_release165 import TARGETS
from check_nes_check165 import inspect
from check_nes_retire165 import nominal

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','reproduced','test']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();d=a.candidate;m=json.loads((d/'preparation.json').read_bytes())
 assert m==json.loads((a.reproduced/'preparation.json').read_bytes())
 pub=json.loads((ROOT/'analysis/release165-verification.json').read_bytes())
 assert sha(a.baseline/'result.json')==m['baseline_result_sha256']==pub['raw_result_sha256']['map01']
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
 def rows(name):return list(csv.DictReader((d/name).open(),delimiter='\t'))
 target=rows('state165-paths.tsv');assert len(target)==3
 settings=rows('release165-settings.tsv');assert {r['target']:r['value'] for r in settings}==dict.fromkeys(TARGETS,'ON')
 topology=rows('release165-topology.tsv');chains=rows('release165-paths.tsv');assert len(chains)==15
 for name in ['records','prepared']:
  first=[r for r in topology if r['chain']==name and r['stage']=='0'];assert len(first)==1
  assert first[0]['to']==first[0]['from'][:-2]+'1]'
 assert all(float(r['slack'])>=0 for r in chains if r['group']!='held')
 for stem in ['state165','release165']:
  assert sha(d/(stem+'-paths.tcl'))==sha(ROOT/'tools'/('nes_'+stem+'_paths.tcl'))
 public={**m['public_sources'],**t['public_sources']}
 for n in ['check_nes_state165.py','nes_state165_paths.tcl','nes_release165.py','nes_release165_paths.tcl','check_nes_check165.py','check_nes_oam_port165.py','check_nes_retire165.py','check_nes_retire165_nominal.py','nes_secondary165_timing.tcl','nes_predecode165_paths.tcl']:
  public['tools/'+n]=sha(ROOT/'tools'/n)
 for n,h in public.items():assert sha(ROOT/n)==h,n
 result={**inspect(d),'nominal':nominal(d),'baseline_nominal':nominal(a.baseline),
  'begin_to_state_setup_ns':min(float(r['slack']) for r in target),
  'release_to_held_setup_ns':min(float(r['slack']) for r in chains if r['group']=='held'),
  'local_release_chain_setup_hold_pass':True,'functional_test':t,'source_byte_reproduction':True,'unchanged_files':60,
  'scope':'Loader state equations separated; original timer, data and fault/error priority preserved. Seeded one-step comparison plus actual one-byte command/reset sequences, not full-ROM load, complete-state formal proof, new game boot or MCU/SNES run. Exact old SPI/reader RTL evidence reused. New fit and local release chains checked; external IO/CDC/reset signoff remains open.',
  'cartridge_sram_reserved':True,'hardware_package':False,'public_sources':public}
 assert not (d/'result.json').exists();(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['fit_le','used_labs','nominal','begin_to_state_setup_ns','release_to_held_setup_ns']}))
if __name__=='__main__':main()
