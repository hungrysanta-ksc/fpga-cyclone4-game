# SPDX-License-Identifier: MIT
"""Parallel CHECK state equations, retaining the existing C3 retirement edge."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import sha

def transform(s):
 a=s.index(' task automatic fail(');b=s.index(' always @(posedge mem_clk or posedge reset)begin',a)
 s=s[:a]+''' // State transitions are independent of the payload write enable. All live
 // errors still clear state on THIS edge; command and counter timing is unchanged.
 wire state_error=error_hard || error_response || error_overlap || (pending && decoded_error!=0);
 wire command_stop=pending && pending_command==4;
 wire command_begin=pending && pending_command==6;
 wire command_finish=pending && pending_command==9;
 wire state_enable=(check_enable && !command_stop && !command_finish) || command_begin;
 wire state_verified=(verified && !(pending && pending_command==0) && !command_stop && !command_begin) || command_finish;
 wire state_busy=(check_busy && !check_response && !command_stop && !command_begin) || (pending && pending_command==7);
 wire state_done=(check_done || check_response) && !command_stop && !command_begin && !(pending && pending_command==8);
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin
   fault<=0;check_enable<=0;check_busy<=0;check_done<=0;verified<=0;
   checked_data<=0;load_chr32<=0;
  end else if(!fault)begin
   fault<=state_error;
   check_enable<=!state_error && state_enable;
   verified<=!state_error && state_verified;
   check_busy<=!state_error && state_busy;
   check_done<=!state_error && state_done;
   // A valid response is captured even when a queued command itself fails.
   // Hard/response/overlap errors suppress it, exactly as before.
   if(!error_hard && !error_response && !error_overlap && check_response)checked_data<=check_data;
   if(!state_error && pending && pending_command==0)load_chr32<=pending_arg[0];
  end
 end
'''+s[b:]
 old='   load_chr32<=0;\n   fault<=0;\n   check_enable<=0;check_busy<=0;check_done<=0;verified<=0;checked_data<=0;\n'
 assert s.count(old)==1;s=s.replace(old,'')
 a=s.index('   if(!fault)begin\n    // Hard faults');b=s.index('   // A complete coherent status snapshot',a)
 s=s[:a]+s[b:]
 return s

def prepare(prior,out):
 assert str(out).isascii() and not out.exists();out.mkdir(parents=True)
 m=json.loads((prior/'preparation.json').read_bytes());pins=m['sources']
 for n,h in pins.items():
  assert sha(prior/n)==h,n;p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(prior/n,p)
 p=out/'nes_rom_spi.sv';p.write_text(transform(p.read_text()),encoding='utf8',newline='\n')
 changed=[n for n in pins if sha(out/n)!=pins[n]];assert changed==['nes_rom_spi.sv']
 m.update(baseline_checkstate_sources=pins,sources={n:sha(out/n) for n in pins},changed=changed,
  checkstate_generator_sha256=sha(Path(__file__)),adopted=False,hardware=False)
 (out/'preparation.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf8');return m
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.prior,a.out)
