# SPDX-License-Identifier: MIT
"""Local same-edge response qualifications for sticky fault and CHECK state."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_board204 import ROOT,BASE,sha,replace
def transform(s):
 anchor=' always @(posedge mem_clk or posedge reset)begin\n  if(reset)begin\n   fault<=0;check_enable<=0;check_busy<=0;check_done<=0;verified<=0;'
 replacement=''' // 220: keep the two response halves local to their state destinations.
 // The original encoded-error priority and checked-data admission are intact.
 wire state_base_bad=error_hard || error_overlap || (pending && decoded_error!=0) ||
   (check_response && (!check_enable || !check_busy));
 (* keep *) wire fault_response_low=check_response && (check_response_address[8:0]!=check_request_tag[8:0]);
 (* keep *) wire fault_response_high=check_response && (check_response_address[18:9]!=check_request_tag[18:9]);
 (* keep *) wire [3:0] state_response_low={state_done,state_busy,state_verified,state_enable} &
   {4{!check_response || check_response_address[8:0]==check_request_tag[8:0]}};
 (* keep *) wire [3:0] state_response_high={state_done,state_busy,state_verified,state_enable} &
   {4{!check_response || check_response_address[18:9]==check_request_tag[18:9]}};
 always @(posedge mem_clk or posedge reset)
  if(reset)fault<=0;
  else fault<=fault || state_base_bad || fault_response_low || fault_response_high;
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin
   check_enable<=0;check_busy<=0;check_done<=0;verified<=0;'''
 s=replace(s,anchor,replacement)
 s=replace(s,'''   fault<=state_error;
   check_enable<=!state_error && state_enable;
   verified<=!state_error && state_verified;
   check_busy<=!state_error && state_busy;
   check_done<=!state_error && state_done;''','''   {check_done,check_busy,verified,check_enable}<=state_response_low & state_response_high & {4{!state_base_bad}};''')
 return s
def prepare(out):
 old=BASE/'probes/nes-status220/source01';p=json.loads((old/'preparation220.json').read_bytes());out.mkdir(parents=True,exist_ok=False)
 for n,h in p['sources'].items():
  assert sha(old/n)==h,n
  (out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,out/n)
 n='nes_rom_spi.sv';before=(old/n).read_text();after=transform(before)
 (out/n).write_text(after,encoding='utf8',newline='\n')
 (out/'response.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True))),encoding='utf8')
 r=dict(sources={n:sha(out/n) for n in p['sources']},baseline=p['baseline'],changed=['nes_rom_loader.sv','nes_rom_spi.sv'],
  public_sources=p['public_sources']|{str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},adopted=False,no_package=True)
 assert sorted(n for n,h in r['sources'].items() if h!=r['baseline'][n])==r['changed']
 (out/'preparation220.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(changed=r['changed'],files=len(r['sources']))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
