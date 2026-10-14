# SPDX-License-Identifier: MIT
"""Keep zero before first SPI fault; capture priority code on the same edge.

Invariant from reset: !fault => error_code==0. Thus zero may be explicitly
rewritten on ordinary cycles; error-code CE no longer depends on live errors.
No new command stage, synthesis attribute, clock or protocol change.
"""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import sha

def transform(s):
 assert s.count('error_code<=code;')==1 and s.count('error_code<=0;')==1
 s=s.replace('error_code<=code;','').replace('error_code<=0;','')
 needle=' task automatic fail(input [3:0] code);'
 assert s.count(needle)==1
 block=''' // Reachable invariant: !fault implies error_code==0. Reset establishes
 // it; every nonzero code and fault latch together. After fault both hold.
 // An explicit zero removes live-error qualification from the hold enable.
 wire error_hard=check_fault || (check_enable && boot_fault);
 wire error_response=check_response && (!check_enable || !check_busy || check_response_address!=check_request_tag);
 wire error_overlap=(sampled || captured || pending || counter_commit_pending) && !ss_sync[1];
 always @(posedge mem_clk or posedge reset)
  if(reset)error_code<=0;
  else if(!fault)error_code<=error_hard?4'd9:error_response?4'd7:error_overlap?4'd1:pending?decoded_error:4'd0;
'''
 return s.replace(needle,block+needle)

def prepare(baseline,out):
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True,exist_ok=False)
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 n='nes_rom_spi.sv';(out/n).write_text(transform((baseline/n).read_text()),encoding='utf8',newline='\n')
 r=dict(baseline=m['sources'],sources={n:sha(out/n) for n in m['sources']},changed=[n],public_sources={'tools/nes_errorzero174.py':sha(Path(__file__))})
 assert [n for n,h in r['sources'].items() if h!=r['baseline'][n]]==[n]
 (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n');return r
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
