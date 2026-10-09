# SPDX-License-Identifier: MIT
"""Reuse129 mapping, run standard fitter effort without changing timing budgets."""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_reader129 import ROOT,sha,put
def main():
 p=argparse.ArgumentParser()
 for n in ['candidate','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists() and str(o).isascii()
 m=json.loads((a.candidate/'fit129.json').read_bytes());assert m['phases']==[dict(phase=n,returncode=0) for n in ['map','fit','sta']]
 assert sha(a.candidate/'nes_rom_spi.sv')==sha(ROOT/'src/nes/diagnostic/nes_rom_spi128.sv')
 shutil.copytree(a.candidate,o)
 inputs={p.relative_to(a.candidate).as_posix():sha(p) for p in a.candidate.rglob('*') if p.is_file()}
 put(o/'refit129-inputs.json',json.dumps(inputs,indent=2)+'\n')
 q=o/'live.qsf';s=q.read_text();assert 'FITTER_EFFORT' not in s
 put(q,s+'\nset_global_assignment -name FITTER_EFFORT "STANDARD FIT"\n')
 shutil.copy2(__file__,o/'executed-nes_reader129_refit.py')
 m.update(refit_only=True,fitter_effort='STANDARD FIT',phases=[])
 # Do not expose the copied candidate's completed phases while refit is running.
 put(o/'fit129.json',json.dumps(m,indent=2)+'\n')
 for phase in ['fit','sta']:
  with (o/(phase+'129.log')).open('wb') as log:r=subprocess.run([str(a.quartus_bin/('quartus_'+phase+'.exe')),'live'],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
  m['phases'].append(dict(phase=phase,returncode=r.returncode));put(o/'fit129.json',json.dumps(m,indent=2)+'\n')
  assert r.returncode==0,phase
 print('PASS129 standard refit phases; audit new timing before acceptance')
if __name__=='__main__':main()
