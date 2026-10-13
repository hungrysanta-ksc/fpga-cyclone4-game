# SPDX-License-Identifier: MIT
"""Use Quartus documented numeric keep=1 for the live comparator tree."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha
from nes_length165 import transform as balanced

def transform(s):
 s=balanced(s)
 assert s.count('(* keep = "true" *)')==2
 return s.replace('(* keep = "true" *)','(* keep = 1 *)')

def prepare(baseline,out):
 assert not out.exists() and str(out).isascii()
 pub=json.loads((ROOT/'analysis/phaseguard165-verification.json').read_bytes())
 assert sha(baseline/'result.json')==pub['raw_result_sha256']['map01']
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir()
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 old=(baseline/'nes_rom_spi.sv').read_text();new=transform(old)
 (out/'nes_rom_spi.sv').write_text(new)
 (out/'spi.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
 result=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],baseline_result_sha256=sha(baseline/'result.json'),changed=['nes_rom_spi.sv'],public_sources={n:sha(ROOT/n) for n in ['tools/nes_length165.py','tools/nes_lengthkeep165.py']})
 assert [n for n,h in result['sources'].items() if h!=m['sources'][n]]==result['changed']
 (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
