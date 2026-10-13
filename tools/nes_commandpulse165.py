# SPDX-License-Identifier: MIT
"""Register six approved command pulses before live-fault retirement gating."""
from pathlib import Path
import argparse,json,difflib
from nes_game147 import ROOT,sha
from nes_commandpayload165 import transform as payload,prepare as prepare_payload

def transform(s):
 s=payload(s)
 def edit(a,b):
  nonlocal s
  assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
 edit('load_begin<=0;load_chr32<=0;load_valid<=0;load_end<=0;start<=0;stop<=0;','load_chr32<=0;')
 edit('   load_begin<=0;load_valid<=0;load_end<=0;start<=0;stop<=0;\n','')
 assert s.count('check_request<=0;')==2;s=s.replace('check_request<=0;','')
 for a,b in [("4'h0:begin load_begin<=1;load_chr32", "4'h0:begin load_chr32"),
             ("4'h1:load_valid<=1;", "4'h1:;"), ("4'h2:load_end<=1;", "4'h2:;"),
             ("4'h3:start<=1;", "4'h3:;"), ("4'h4:begin stop<=1;", "4'h4:begin "),
             ("4'h7:begin check_request<=1;check_busy<=1;end", "4'h7:check_busy<=1;")]:edit(a,b)
 at=' task automatic fail(input [3:0] code);begin'
 block=''' // C1 validates and decodes the command. C2 applies ONLY live fault/SS
 // gating to the pulse registers. No error delay and no extra clock stage.
 // Bit order: BEGIN, DATA, END, START, STOP, CHECK_READ.
 reg [5:0] approved_pulse;
 wire command_retire_ok=!fault && ss_sync[1] && !check_fault &&
  !(check_enable && boot_fault) &&
  !(check_response && (!check_enable || !check_busy || check_response_address!=check_request_tag));
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin
   approved_pulse<=0;
   load_begin<=0;load_valid<=0;load_end<=0;start<=0;stop<=0;check_request<=0;
  end else begin
   approved_pulse<=0;
   if(captured)begin
'''
 for i,op in enumerate([0,1,2,3,4,7]):
  block+=f"    approved_pulse[{i}]<=pending_header_error==0 && pending_causes==0 && pending_command==4'h{op:x};\n"
 block+='''   end
   {check_request,stop,start,load_end,load_valid,load_begin}<=approved_pulse & {6{command_retire_ok}};
  end
 end
'''
 edit(at,block+at)
 return s

def prepare(baseline,out):
 prepare_payload(baseline,out)
 old=(baseline/'nes_rom_spi.sv').read_text();new=transform(old)
 (out/'nes_rom_spi.sv').write_text(new)
 (out/'spi.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
 p=out/'preparation.json';r=json.loads(p.read_bytes());r['sources']['nes_rom_spi.sv']=sha(out/'nes_rom_spi.sv')
 r['public_sources']['tools/nes_commandpulse165.py']=sha(Path(__file__));r['preapproved_pulses']=6
 p.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
