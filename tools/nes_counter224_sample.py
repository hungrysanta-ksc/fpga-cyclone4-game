# SPDX-License-Identifier: MIT
"""Capture eligibility every edge, consume only original C0 sample at C1."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_counter224 import ROOT,BASE,sha,replace,transform as counter

def sample(s):
 s=replace(s,' reg raw_loaded,raw_run,raw_ready,raw_load_ready;', ''' reg raw_loaded,raw_run,raw_ready,raw_load_ready;
 //224: C1 reads these only when sampled is high from the preceding C0.
 // Continuously sampling removes command decode from their capture enable,
 // without moving the consumed external values to an earlier/later edge.
 always @(posedge mem_clk or posedge reset)
  if(reset)begin raw_loaded<=0;raw_run<=0;raw_ready<=0;raw_load_ready<=0;end
  else begin raw_loaded<=loaded;raw_run<=run_enable;raw_ready<=check_ready;raw_load_ready<=load_ready;end''')
 # Remove only the former conditional assignments; keep new dedicated block.
 s=replace(s,'sampled<=0;raw_causes<=0;raw_select<=0;raw_loaded<=0;raw_run<=0;raw_ready<=0;raw_load_ready<=0;captured<=0;',
              'sampled<=0;raw_causes<=0;raw_select<=0;captured<=0;')
 s=replace(s,'     raw_loaded<=loaded;raw_run<=run_enable;raw_ready<=check_ready;raw_load_ready<=load_ready;','')
 return s

def transform(s):return sample(counter(s))

def prepare(out):
 old=BASE/'probes/nes-counter224/source01';p=json.loads((old/'preparation224.json').read_bytes())
 out.mkdir(parents=True,exist_ok=False)
 for n,h in p['sources'].items():
  assert sha(old/n)==h,n;(out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,out/n)
 before=(old/'nes_rom_spi.sv').read_text();after=sample(before)
 assert after==transform((BASE/'probes/nes-ingress223/source01/nes_rom_spi.sv').read_text())
 (out/'nes_rom_spi.sv').write_text(after,encoding='utf8',newline='\n')
 (out/'sample.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True))),encoding='utf8',newline='\n')
 p['sources']={n:sha(out/n) for n in p['sources']};p['sampling_every_edge_consumed_at_original_C0']=True
 p['public_source_sha256']=sha(Path(__file__))
 (out/'preparation224.json').write_text(json.dumps(p,indent=2)+'\n',encoding='utf8',newline='\n')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
