# SPDX-License-Identifier: MIT
"""Bind same-edge loader proof, wire replay and independently routed candidates."""
from pathlib import Path
import argparse,json,csv
from nes_game147 import ROOT,sha
from nes_legality174 import transform
from nes_errorhold174 import transform as errorhold
from check_nes_retire165 import nominal
from check_nes_check165 import inspect
from check_nes_boundary165 import measurements

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','map01','map02','test','spi','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 b=json.loads((a.baseline/'preparation.json').read_bytes())['sources']
 t=json.loads((a.test/'result.json').read_bytes());s=json.loads((a.spi/'result.json').read_bytes())
 assert t['passed'] and t['states']==294912 and t['sequences']==1056 and len(t['negatives'])==3
 assert s['passed'] and s['wire_bits']==14016
 assert t['source_sha256']==sha(a.map01/'nes_rom_loader.sv') and t['reference_sha256']==b['nes_rom_loader.sv']
 for n,h in s['sources'].items():
  assert sha(a.spi/n)==h,n
  if n in b:assert sha(a.map01/n)==h,n
 assert (a.map01/'nes_rom_loader.sv').read_text()==transform((a.baseline/'nes_rom_loader.sv').read_text())
 assert (a.map02/'nes_rom_spi.sv').read_text()==errorhold((a.map01/'nes_rom_spi.sv').read_text())
 results={}
 for label,d in [('map01',a.map01),('map02',a.map02)]:
  m=json.loads((d/'preparation.json').read_bytes())
  for n,h in m['sources'].items():
   assert sha(d/n)==h,n
   if n not in ['nes_rom_loader.sv','nes_rom_spi.sv']:assert h==b[n],n
  assert sha(d/'nes_rom_loader.sv')==t['source_sha256']
  paths=list(csv.DictReader((d/'legality174-paths.tsv').open(),delimiter='\t'))
  regs=(d/'legality174-registers.tsv').read_text().splitlines()[1:];assert len(regs)==4 and len(paths)==18
  assert {n.rsplit('|',1)[-1] for n in regs}=={f'reject_state[{i}]' for i in range(4)}
  results[label]=dict(fit=inspect(d),nominal=nominal(d),targeted={g:{k:min(float(r['slack']) for r in paths if r['group']==g and r['kind']==k) for k in ['setup','hold']} for g in ['datafault','checkfault','legality']},sources=m['sources'],registers=regs)
  results[label]['io']=measurements(d) if (d/'boundary165-paths.tsv').exists() else None
 e=list(csv.DictReader((a.map02/'errorhold174-paths.tsv').open(),delimiter='\t'));assert len(e)==6
 results['map02']['errorhold_setup_ns']=min(float(r['slack']) for r in e if r['kind']=='setup')
 # Attribute-only follow-up: behavior and protocol source are exactly map01
 # after this single synthesis attribute substitution; SPI replay is reused.
 pub={**t['public_sources'],**s['public_sources']}
 for n in ['tools/check_nes_legality174.py','tools/nes_legality174_paths.tcl','tools/nes_errorhold174.py','tools/nes_errorhold174_paths.tcl','tools/check_nes_check165.py','tools/check_nes_retire165.py','tools/check_nes_boundary165.py']:pub[n]=sha(ROOT/n)
 for n,h in pub.items():assert sha(ROOT/n)==h,n
 r=dict(functional_passed=True,hardware_package=False,physical=False,results=results,loader=t,spi=s,extra_command_cycles=0,save_sram_used=False,unchanged_from_cross174_except=['nes_rom_loader.sv','nes_rom_spi.sv'],spi_map02_behavior_reused=True,public_sources=pub)
 a.out.write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:dict(passed=v['nominal']['passed'],worst=v['nominal']['worst_setup'],le=v['fit']['fit_le'],labs=v['fit']['used_labs'],targeted=v['targeted']) for k,v in results.items()}))
if __name__=='__main__':main()
