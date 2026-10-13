# SPDX-License-Identifier: MIT
"""Split same-edge STOP offset validation from static counter-clear eligibility."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha

def transform(s):
 old=' reg pending_counter_clear,pending_counter_inc;'
 assert s.count(old)==1
 s=s.replace(old,''' reg pending_other_clear,pending_stop_clear,pending_stop_offset_ok,pending_counter_inc;
 // Capture all operands at the original SS-rise edge. Do not pre-sample
 // loaded_bytes: an in-flight loader write may retire during this frame.
 wire pending_counter_clear=pending_other_clear || (pending_stop_clear && pending_stop_offset_ok);''')
 old='pending_counter_clear<=0;';assert s.count(old)==1
 s=s.replace(old,'pending_other_clear<=0;pending_stop_clear<=0;pending_stop_offset_ok<=0;')
 old="""     pending_counter_clear<=counter_header_ok &&
      ((cmd60 && arg==2 && offset==0 && !check_enable) ||
       (cmd64 && arg==0 && offset=={5'd0,loaded_bytes}) ||
       (cmd66 && arg==0 && offset==0 && loaded && !run_enable && !check_enable));"""
 new="""     pending_other_clear<=counter_header_ok &&
      ((cmd60 && arg==2 && offset==0 && !check_enable) ||
       (cmd66 && arg==0 && offset==0 && loaded && !run_enable && !check_enable));
     pending_stop_clear<=counter_header_ok && cmd64 && arg==0;
     pending_stop_offset_ok<=offset=={5'd0,loaded_bytes};"""
 assert s.count(old)==1
 return s.replace(old,new)

def prepare(baseline,out):
 assert not out.exists() and str(out).isascii()
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir()
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 old=(baseline/'nes_rom_spi.sv').read_text();new=transform(old)
 (out/'nes_rom_spi.sv').write_text(new)
 (out/'spi.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
 result=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],baseline_result_sha256=sha(baseline/'result.json'),changed=['nes_rom_spi.sv'],public_sources={'tools/nes_stopclear165.py':sha(Path(__file__))})
 assert [n for n,h in result['sources'].items() if h!=m['sources'][n]]==result['changed']
 (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
