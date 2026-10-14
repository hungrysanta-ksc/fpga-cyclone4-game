# SPDX-License-Identifier: MIT
"""Use D feedback instead of synthesized CE for four SPI error-code bits.

Selected after legality174 routed check_busy->error_code ena failed -0.098ns.
No behavioral RTL change; no clock relaxation or speculative seed sweep.
"""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import sha
ATTRIBUTE='(* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF; -name ALLOW_SYNCH_CTRL_USAGE OFF" *) '
def transform(s):
 n='output reg fault,output reg [3:0] error_code,';assert s.count(n)==1
 return s.replace(n,'output reg fault,\n '+ATTRIBUTE+'output reg [3:0] error_code,')
def prepare(baseline,out):
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True,exist_ok=False)
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 n='nes_rom_spi.sv';(out/n).write_text(transform((baseline/n).read_text()),encoding='utf8',newline='\n')
 r=dict(baseline=m['sources'],sources={n:sha(out/n) for n in m['sources']},changed=['nes_rom_spi.sv'],public_sources={'tools/nes_errorhold174.py':sha(Path(__file__))})
 assert [n for n,h in r['sources'].items() if h!=r['baseline'][n]]==['nes_rom_spi.sv']
 (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
