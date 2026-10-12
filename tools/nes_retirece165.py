# SPDX-License-Identifier: MIT
"""Use a dedicated CHECK counter update enable with same-edge fault priority."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha
from nes_lengthkeep165 import transform as balanced

def transform(s):
 s=balanced(s)
 old='(* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF; -name ALLOW_SYNCH_CTRL_USAGE OFF" *) reg [18:0] check_next;'
 assert s.count(old)==1
 s=s.replace(old,old.replace('RECOGNITION OFF','RECOGNITION ON'))
 old=' always @(posedge mem_clk or posedge reset)\n  if(reset)check_next<=0;\n  else if(counter_retire_ok)begin'
 new=''' // Dedicated register enable, not a gated clock. Fault/response ownership
 // still suppress the update on the original retirement edge.
 (* altera_attribute="-name IMPLEMENT_AS_CLOCK_ENABLE ON" *) wire counter_update_enable;
 assign counter_update_enable=counter_retire_ok && (pending_counter_clear || pending_counter_inc);
 always @(posedge mem_clk or posedge reset)
  if(reset)check_next<=0;
  else if(counter_update_enable)begin'''
 assert s.count(old)==1;s=s.replace(old,new)
 assert s.count('else if(pending_counter_inc)begin')==1
 return s.replace('else if(pending_counter_inc)begin','else begin')

def prepare(baseline,out):
 assert not out.exists() and str(out).isascii()
 v=json.loads((ROOT/'analysis/phaseguard165-verification.json').read_bytes())
 assert sha(baseline/'result.json')==v['raw_result_sha256']['map01']
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir()
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 old=(baseline/'nes_rom_spi.sv').read_text();new=transform(old)
 (out/'nes_rom_spi.sv').write_text(new)
 (out/'spi.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
 r=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],baseline_result_sha256=sha(baseline/'result.json'),changed=['nes_rom_spi.sv'],public_sources={n:sha(ROOT/n) for n in ['tools/nes_retirece165.py','tools/nes_length165.py','tools/nes_lengthkeep165.py']})
 assert [n for n,h in r['sources'].items() if h!=m['sources'][n]]==r['changed']
 (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
