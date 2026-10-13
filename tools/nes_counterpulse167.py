# SPDX-License-Identifier: MIT
"""Qualify counter actions in C1, without changing C2 fault/response priority."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha

def transform(s):
 old='wire counter_retire_ok=!fault && pending && ss_sync[1] && !check_fault &&'
 assert s.count(old)==1
 s=s.replace(old,'wire counter_retire_ok=!fault && ss_sync[1] && !check_fault &&')
 old='   pending<=captured;captured<=0;'
 assert s.count(old)==1
 s=s.replace(old,'''   pending<=captured;captured<=0;
   // C1 emits single-cycle counter actions, just like approved_pulse.
   // Invariant: action implies pending. The live C2 fault/SS/response
   // checks remain unchanged; no early response-address sample is used.
   pending_counter_clear<=0;pending_counter_inc<=0;''')
 return s

def prepare(baseline,out):
 assert not out.exists() and str(out).isascii()
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True)
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 n='nes_rom_spi.sv';old=(out/n).read_text();new=transform(old)
 (out/n).write_text(new,encoding='utf8',newline='\n')
 (out/'counter.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))),encoding='utf8')
 r=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],changed=[n],baseline_preparation_sha256=sha(baseline/'preparation.json'),public_sources={'tools/nes_counterpulse167.py':sha(Path(__file__))})
 assert [n for n,h in r['sources'].items() if h!=m['sources'][n]]==r['changed']
 (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
