# SPDX-License-Identifier: MIT
"""Keep loader permission off the increment data path; no clock or latency change."""
from pathlib import Path
import argparse,json,difflib
from nes_game147 import ROOT,sha
from nes_counterpulse167 import prepare as parent

def transform(s):
 old='(* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF; -name ALLOW_SYNCH_CTRL_USAGE OFF" *) output reg [18:0] loaded_bytes,'
 assert s.count(old)==1;s=s.replace(old,old.replace('RECOGNITION OFF','RECOGNITION ON'))
 old=''' always @(posedge mem_clk or posedge reset)begin
  if(reset)begin loaded_bytes<=0;count_complete<=0;end
  else if(active_reset)begin loaded_bytes<=0;count_complete<=0;end
  else if(!fault)begin
   if(count_stop || count_begin)begin loaded_bytes<=0;count_complete<=0;end
   else if(count_advance)begin loaded_bytes<=loaded_bytes+1'b1;count_complete<=loaded_bytes==total-1'b1;end
  end
 end'''
 assert s.count(old)==1
 new=''' // A dedicated register enable keeps the live command/state predicate
 // outside the carry data. This is not a gated clock; clear still wins.
 wire count_update=active_reset || (!fault && (count_stop || count_begin || count_advance));
 wire count_clear=active_reset || count_stop || count_begin;
 always @(posedge mem_clk or posedge reset)begin
  if(reset)loaded_bytes<=0;
  else if(count_update)begin
   if(count_clear)loaded_bytes<=0;
   else begin
'''
 new+='\n'.join(f'    loaded_bytes[{i}]<=loaded_bytes[{i}] ^ '+("1'b1;" if i==0 else f'(&loaded_bytes[{i-1}:0]);') for i in range(19))
 new+='''
   end
  end
 end
 always @(posedge mem_clk or posedge reset)begin
  if(reset)count_complete<=0;
  else if(active_reset)count_complete<=0;
  else if(!fault)begin
   if(count_stop || count_begin)count_complete<=0;
   else if(count_advance)count_complete<=loaded_bytes==total-1'b1;
  end
 end'''
 return s.replace(old,new)

def prepare(baseline,out):
 parent(baseline,out);m=json.loads((out/'preparation.json').read_bytes())
 p=out/'nes_rom_loader.sv';old=p.read_text();new=transform(old);p.write_text(new,encoding='utf8',newline='\n')
 (out/'loader.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))),encoding='utf8')
 m['sources']['nes_rom_loader.sv']=sha(p);m['changed'].append('nes_rom_loader.sv');m['public_sources']['tools/nes_loadcount167.py']=sha(Path(__file__))
 (out/'preparation.json').write_text(json.dumps(m,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
