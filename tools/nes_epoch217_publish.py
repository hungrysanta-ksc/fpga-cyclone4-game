# SPDX-License-Identifier: MIT
"""Separate serial increment from Gray publication; hold admission until publish."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_board204 import ROOT,BASE,sha,replace

def transform(s):
 s=replace(s,'serial<=0;gray<=0;exhausted<=0;','serial<=0;exhausted<=0;')
 s=replace(s,'serial<=next_serial;gray<=next_serial^(next_serial>>1);','serial<=next_serial;')
 s=replace(s,' // This loader accepts exactly', ''' // Gray publication follows serial by one memory edge. BEGIN invalidates
 // immediately; pending holds invalid even if mem_clk stops before publish.
 // No new frame delay: content ID only changes on a ROM load.
 reg gray_pending;
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin gray<=0;gray_pending<=0;end
  else begin gray<=serial^(serial>>1);gray_pending<=load_begin;end
 end
 // This loader accepts exactly''')
 return replace(s,'reset||cold_reset||exhausted','reset||cold_reset||gray_pending||exhausted')

def prepare(out):
 old=BASE/'probes/nes-loader217/source01';p=json.loads((old/'preparation217.json').read_bytes());out.mkdir(parents=True,exist_ok=False)
 for n,h in p['sources'].items():
  assert sha(old/n)==h,n;(out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,out/n)
 before=(old/'nes_source_epoch207.sv').read_text();after=transform(before)
 (out/'nes_source_epoch207.sv').write_text(after,encoding='utf8',newline='\n')
 (out/'epoch.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True))),encoding='utf8')
 r=dict(sources={n:sha(out/n) for n in p['sources']},baseline=p['baseline'],changed=['nes_rom_loader.sv','nes_source_epoch207.sv'],
  public_sources=p['public_sources']|{str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},no_package=True,adopted=False)
 assert sorted(n for n,h in r['sources'].items() if h!=r['baseline'][n])==r['changed']
 (out/'preparation217.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(changed=r['changed'],files=len(r['sources']))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
