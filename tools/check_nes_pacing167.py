# SPDX-License-Identifier: MIT
"""Candidate boundaries, conditional routed timing and local equivalence."""
from pathlib import Path
import argparse,json,re
from nes_game147 import ROOT,sha
from nes_pacing167 import fill,exporter,joint
from check_nes_check165 import inspect
from check_nes_retire165 import nominal
from check_nes_boundary165 import measurements
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','equiv','reference']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();d=a.candidate;m=json.loads((d/'preparation.json').read_bytes())
 assert len(m['sources'])==61 and len(m['changed']) in [3,4]
 transforms={'nes_native_fill165.sv':fill,'nes_native_export165.sv':exporter,'nes_live_joint.sv':joint}
 if 'board.qsf' in m['changed']:
  transforms['board.qsf']=lambda s:s+'\nset_global_assignment -name FITTER_EFFORT STANDARD_FIT\n'+('set_global_assignment -name PLACEMENT_EFFORT_MULTIPLIER 2.0\n' if m.get('placement_effort') else '')
  assert re.search(r'Fitter Effort\s*; Standard Fit', (d/'output_files/board.fit.rpt').read_text())
  if m.get('placement_effort'):assert re.search(r'Placement Effort Multiplier\s*; 2.0', (d/'output_files/board.fit.rpt').read_text())
 for n,h in m['sources'].items():
  assert sha(d/n)==h and sha(a.baseline/n)==m['baseline'][n],n
  if n in transforms:assert (d/n).read_text()==transforms[n]((a.baseline/n).read_text())
  else:assert h==m['baseline'][n],n
 e=json.loads((a.equiv/'result.json').read_bytes());r=json.loads((a.reference/'result.json').read_bytes())
 assert e['passed'] and e['modes']==18 and r['passed']
 assert e['candidate_sha256']==sha(d/'nes_native_fill165.sv') and e['reference_result_sha256']==sha(a.reference/'result.json')
 for n in ['nes_native_export165.sv','nes_native_arbiter165.sv']:assert sha(d/n)==sha(a.reference/n),n
 # Public final pins do not reinterpret reference result's exit-time tool pins.
 # Executed RTL/tool copies and the publication addendum identify that run.
 v=inspect(d);n=nominal(d);io=measurements(d)
 passed=n['passed'] and io['conditional_data_bounds_pass'] and io['native_payload_reset_pass']
 result=dict(passed=passed,fit=v,nominal=n,io=io,unchanged_files=61-len(transforms),equivalence=e,reference_result_sha256=sha(a.reference/'result.json'),reference_copies={x:sha(a.reference/x) for x in ['nes_native_fill165.sv','nes_native_export165.sv','nes_native_arbiter165.sv','nes_pacing167.py','test_nes_pacing167.py','native_pacing167_tb.sv']},physical=False,full_io_approved=False,public_sources={x:sha(ROOT/x) for x in ['tools/nes_pacing167.py','tools/check_nes_pacing167.py','tools/check_nes_check165.py','tools/check_nes_retire165.py','tools/check_nes_boundary165.py','tools/nes_boundary165_paths.tcl','tools/test_nes_pacing167_equiv.py']})
 assert not (d/'result.json').exists();(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(passed=passed,le=v['fit_le'],labs=v['used_labs'],setup=n['worst_setup'],io=io['conditional_data_bounds_pass'],payload_reset=io['native_payload_reset_pass'])))
if __name__=='__main__':main()
