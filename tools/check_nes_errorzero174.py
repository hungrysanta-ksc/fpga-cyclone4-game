# SPDX-License-Identifier: MIT
"""Bind error-code invariant proof and actual SPI to routed source pins."""
from pathlib import Path
import argparse,json,csv
from nes_game147 import ROOT,sha
from nes_errorzero174 import transform
from check_nes_check165 import inspect
from check_nes_retire165 import nominal
from check_nes_boundary165 import measurements

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','fit','test','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--io',type=Path)
 a=p.parse_args();assert not a.out.exists()
 b=json.loads((a.baseline/'preparation.json').read_bytes())['sources']
 m=json.loads((a.fit/'preparation.json').read_bytes());t=json.loads((a.test/'result.json').read_bytes())
 assert t['passed'] and t['states']==557056 and len(t['negatives'])==2
 assert t['reference_sha256']==b['nes_rom_spi.sv']
 assert (a.fit/'nes_rom_spi.sv').read_text()==transform((a.baseline/'nes_rom_spi.sv').read_text())
 assert m['baseline']==b
 for n,h in m['sources'].items():
  assert sha(a.fit/n)==h,n
  if n!='nes_rom_spi.sv':assert h==b[n],n
 for n,h in t['sources'].items():
  assert sha(a.test/n)==h,n
  if n in b:assert h==m['sources'][n],n
 paths=list(csv.DictReader((a.fit/'errorhold174-paths.tsv').open(),delimiter='\t'));assert len(paths)==6
 f=inspect(a.fit);timing=nominal(a.fit)
 io=None
 if a.io:
  for n,h in m['sources'].items():assert sha(a.io/n)==h,n
  io=measurements(a.io)
 pub=t['public_sources']|{n:sha(ROOT/n) for n in ['tools/check_nes_errorzero174.py','tools/nes_errorhold174_paths.tcl','tools/check_nes_check165.py','tools/check_nes_retire165.py','tools/check_nes_boundary165.py']}
 for n,h in pub.items():assert sha(ROOT/n)==h,n
 r=dict(functional_passed=True,fit=f,nominal=timing,io=io,targeted_error_setup_ns=min(float(x['slack']) for x in paths if x['kind']=='setup'),
 sources=m['sources'],test=t,extra_command_cycles=0,physical=False,hardware_package=False,public_sources=pub,
 previous_loader_proof='legality174:294912 states/1056 sequences/3 negatives; exact unchanged loader',
 previous_video_proof='cross174 + batch174; no changed collector/MCU/SNES source')
 a.out.write_text(json.dumps(r,indent=2)+'\n',newline='\n')
 print(json.dumps(dict(functional=True,nominal=timing['passed'],worst=timing['worst_setup'],le=f['fit_le'],labs=f['used_labs'],targeted=r['targeted_error_setup_ns'],io=io)))
if __name__=='__main__':main()
