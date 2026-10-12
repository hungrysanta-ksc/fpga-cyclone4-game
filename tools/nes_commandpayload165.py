# SPDX-License-Identifier: MIT
"""Prepare payload before retirement; only load_valid authorizes consumption."""
from pathlib import Path
import argparse,json,difflib
from nes_game147 import ROOT,sha
from nes_commandstage165 import transform as staged,prepare as prepare_stage

def transform(s):
 s=staged(s)
 for a,b in [
  ('   load_data<=0;fault<=0;error_code<=0;','   fault<=0;error_code<=0;'),
  ("4'h1:begin load_valid<=1;load_data<=pending_arg;end","4'h1:load_valid<=1;")]:
  assert s.count(a)==1;s=s.replace(a,b)
 needle=' task automatic fail(input [3:0] code);begin'
 assert s.count(needle)==1
 s=s.replace(needle,''' // Payload may change while load_valid is low, including a rejected DATA.
 // The loader consumes it only on load_valid; faults still suppress that pulse.
 always @(posedge mem_clk or posedge reset)
  if(reset)load_data<=0;
  else if(captured && pending_command==4'h1)load_data<=pending_arg;
'''+needle)
 return s

def prepare(baseline,out):
 prepare_stage(baseline,out)
 old=(baseline/'nes_rom_spi.sv').read_text();new=transform(old)
 (out/'nes_rom_spi.sv').write_text(new)
 (out/'spi.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
 p=out/'preparation.json';r=json.loads(p.read_bytes());r['sources']['nes_rom_spi.sv']=sha(out/'nes_rom_spi.sv')
 r['public_sources']['tools/nes_commandpayload165.py']=sha(Path(__file__));r['invalid_payload_unobservable']=True
 p.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
