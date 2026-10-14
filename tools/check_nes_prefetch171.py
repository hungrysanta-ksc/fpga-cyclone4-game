# SPDX-License-Identifier: MIT
"""Gate171 on exact source reproduction, FIFO tests, routed STA and IO bounds."""
from pathlib import Path
import argparse,json,re
from nes_game147 import ROOT,sha
from nes_prefetch171 import transform
from check_nes_check165 import inspect
from check_nes_retire165 import nominal
from check_nes_boundary165 import measurements
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','test','cancel-test']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();d=a.candidate;m=json.loads((d/'preparation.json').read_bytes())
 assert m['changed']==['nes_native_fill165.sv']
 for n,h in m['sources'].items():
  assert sha(d/n)==h and sha(a.baseline/n)==m['baseline'][n],n
  if n not in m['changed']:assert h==m['baseline'][n],n
 assert (d/'nes_native_fill165.sv').read_text()==transform((a.baseline/'nes_native_fill165.sv').read_text())
 tests=[json.loads((x/'result.json').read_bytes()) for x in [a.test,a.cancel_test]]
 for t in tests:
  assert t['passed'] and t['source_sha256']==m['sources']['nes_native_fill165.sv']
 assert len(tests[0]['results'])==25 and len(tests[1]['results'])==3
 report=(d/'output_files/board.map.rpt').read_text()
 assert re.search(r'fifo_rtl_\d.*M9K\s*; Simple Dual Port.*256\s*; 27',report), 'FIFO inference'
 fit=inspect(d);nt=nominal(d);io=measurements(d)
 pub={**m['public_sources']}
 for t in tests:pub.update(t['public_sources'])
 for n in ['tools/check_nes_prefetch171.py','tools/check_nes_boundary165.py','tools/nes_boundary165_paths.tcl','tools/check_nes_retire165_nominal.py','tools/nes_secondary165_timing.tcl']:pub[n]=sha(ROOT/n)
 for n,h in pub.items():assert sha(ROOT/n)==h,n
 r=dict(passed=nt['passed'] and io['conditional_data_bounds_pass'] and io['native_payload_reset_pass'],fit=fit,nominal=nt,io=io,functional=tests,unchanged_files=len(m['sources'])-1,public_sources=pub,hardware=False,full_io_signoff=False,same_limits=True,save_sram_used=False)
 assert not (d/'result171.json').exists();(d/'result171.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(dict(passed=r['passed'],le=fit['fit_le'],labs=fit['used_labs'],m9k=fit['m9k_blocks'],setup=nt['worst_setup'],io=io['conditional_data_bounds_pass'])))
if __name__=='__main__':main()
