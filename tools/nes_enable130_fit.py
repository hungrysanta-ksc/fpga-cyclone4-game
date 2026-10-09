# SPDX-License-Identifier: MIT
"""Fresh actual-core map/fit after integrating130; resource failure is recorded."""
from pathlib import Path
import argparse,json,subprocess,shutil
from nes_enable130 import ROOT,sha,put,materialize
def main():
 p=argparse.ArgumentParser()
 for n in ['out','baseline','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out.resolve();assert not o.exists() and str(o).isascii();o.mkdir()
 materialize(o,a.baseline,full=True)
 for n in ['nes_enable130.py','nes_enable130_fit.py']:shutil.copy2(ROOT/'tools'/n,o/('executed-'+n))
 m=dict(candidate='NES-LOADER-130',phases=[],fit_passed=False,full_timing_pass=False,installable=False)
 for phase in ['map','fit','sta']:
  with (o/(phase+'130.log')).open('wb') as log:r=subprocess.run([str(a.quartus_bin/('quartus_'+phase+'.exe')),'live'],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
  m['phases'].append(dict(phase=phase,returncode=r.returncode));put(o/'fit130.json',json.dumps(m,indent=2)+'\n')
  if r.returncode:print('STOP130 '+phase+' failed; inspect raw log');return
  if phase=='fit':m['fit_passed']=True
 put(o/'fit130.json',json.dumps(m,indent=2)+'\n');print('PASS130 tool phases; physical timing and new CDC paths still require review')
if __name__=='__main__':main()
