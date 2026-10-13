# SPDX-License-Identifier: MIT
"""Remove redundant conflict decoding in SETUP/RELEASE state retirement."""
from pathlib import Path
import argparse,json,re,shutil,difflib
from nes_game147 import ROOT,sha

OLD="""   SETUP,RELEASE:begin
    if(fault || command_conflict)state<=FAILED;
    else if(stop)state<=IDLE;
    else if(accepted_load_begin || accepted_start || accepted_load_end)state<=FAILED;
    else if(remaining==1)state<=(state==SETUP)?WRITE:RECEIVE;
   end"""
NEW="""   SETUP,RELEASE:begin
    // Every command conflict includes BEGIN, END or START. These commands
    // fail in both timed states even alone, including conflicts with STOP.
    if(fault || accepted_load_begin || accepted_start || accepted_load_end)state<=FAILED;
    else if(stop)state<=IDLE;
    else if(remaining==1)state<=(state==SETUP)?WRITE:RECEIVE;
   end"""

def transform(s):
 assert s.count(OLD)==1
 return s.replace(OLD,NEW)

def prepare(baseline,out):
 assert not out.exists() and str(out).isascii()
 pub=json.loads((ROOT/'analysis/state165-verification.json').read_bytes())
 assert sha(baseline/'result.json')==pub['raw_result_sha256']['map01']
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True)
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 old=(baseline/'nes_rom_loader.sv').read_text();new=transform(old)
 (out/'nes_rom_loader.sv').write_text(new)
 (out/'loader.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
 result=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],baseline_result_sha256=sha(baseline/'result.json'),
  changed=['nes_rom_loader.sv'],public_sources={'tools/nes_phaseguard165.py':sha(Path(__file__))})
 assert [n for n,h in result['sources'].items() if h!=m['sources'][n]]==result['changed']
 (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
