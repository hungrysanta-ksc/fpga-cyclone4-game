# SPDX-License-Identifier: MIT
"""Same-edge local response halves for counter retirement; no extra pipeline."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_board204 import ROOT,BASE,sha,replace

def transform(s):
 s=replace(s,''' wire counter_retire_ok=!fault && pending && ss_sync[1] && !check_fault &&
  !(check_enable && boot_fault) &&
  !(check_response && (!check_enable || !check_busy || check_response_address!=check_request_tag));''',''' //224: qualify each pending counter action locally, on the original edge.
 // Keep address halves independent of shared encoded error_response routing.
 wire counter_base_ok=!fault && pending && ss_sync[1] && !check_fault &&
  !(check_enable && boot_fault) && !(check_response && (!check_enable || !check_busy));
 (* keep *) wire [1:0] counter_low={pending_counter_clear,pending_counter_inc} &
  {2{!check_response || check_response_address[8:0]==check_request_tag[8:0]}};
 (* keep *) wire [1:0] counter_high={pending_counter_clear,pending_counter_inc} &
  {2{!check_response || check_response_address[18:9]==check_request_tag[18:9]}};''')
 return replace(s,'''   commit_clear<=counter_retire_ok && pending_counter_clear;
   commit_inc<=counter_retire_ok && pending_counter_inc;''','''   {commit_clear,commit_inc}<=counter_low & counter_high & {2{counter_base_ok}};''')

def prepare(out):
 old=BASE/'probes/nes-ingress223/source01'
 pins=json.loads((old/'preparation-ingress223.json').read_bytes())['sources']
 manifest=json.loads((old.parent/'manifest01.json').read_bytes())
 out.mkdir(parents=True,exist_ok=False)
 for n,h in pins.items():
  assert sha(old/n)==h==manifest['source01/'+n],n
  (out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,out/n)
 before=(old/'nes_rom_spi.sv').read_text();after=transform(before)
 (out/'nes_rom_spi.sv').write_text(after,encoding='utf8',newline='\n')
 sources={n:sha(out/n) for n in pins};changed=[n for n,h in sources.items() if h!=pins[n]]
 assert changed==['nes_rom_spi.sv']
 (out/'counter.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True))),encoding='utf8',newline='\n')
 result=dict(sources=sources,baseline=pins,changed=changed,wire_version='2231',arm_unchanged=True,
             public_source_sha256=sha(Path(__file__)),adopted=False,no_package=True)
 (out/'preparation224.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(files=len(sources),changed=changed)))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
