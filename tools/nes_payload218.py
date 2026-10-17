# SPDX-License-Identifier: MIT
"""Flatten loader payload admission; retain the original capture and pin edges."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_board204 import ROOT,BASE,sha,replace

def transform(s):
 old=';chr32<=0;chip<=0;lane<=0;byte_hold<=0;load_address<=0;'
 assert s.count(old)==2;s=s.replace(old,';chr32<=0;')
 s=replace(s,"       load_address<={2'd0,byte_address[21:2]};chip<=byte_address[1];lane<=byte_address[0];byte_hold<=load_data;",'       // Payload capture has its own equivalent admission equation below.')
 anchor=' // 217: mutually exclusive error classes, with independent bit hold paths.'
 return replace(s,anchor,''' // 218: the payload has one accepted RECEIVE/DATA edge. Express it
 // directly, rather than through the shared command-conflict priority tree.
 // Higher case arms and STOP still suppress capture; no extra clock stage.
 wire payload_accept=phase[RECEIVE] && !(phase[IDLE] || phase[READY]) &&
   !fault && !commands_blocked && !load_begin && !load_end && !start &&
   !stop && load_valid && !count_complete;
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin chip<=0;lane<=0;byte_hold<=0;load_address<=0;end
  else if(active_reset)begin chip<=0;lane<=0;byte_hold<=0;load_address<=0;end
  else if(payload_accept)begin
   load_address<={2'd0,byte_address[21:2]};chip<=byte_address[1];lane<=byte_address[0];byte_hold<=load_data;
  end
 end

'''+anchor)

def prepare(out):
 old=BASE/'probes/nes-boundary218/source01';p=json.loads((old/'preparation218.json').read_bytes());out.mkdir(parents=True,exist_ok=False)
 for n,h in p['sources'].items():
  assert sha(old/n)==h,n
  (out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,out/n)
 before=(old/'nes_rom_loader.sv').read_text();after=transform(before)
 (out/'nes_rom_loader.sv').write_text(after,encoding='utf8',newline='\n')
 (out/'payload.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True))),encoding='utf8')
 r=dict(sources={n:sha(out/n) for n in p['sources']},baseline=p['baseline'],changed=['nes_rom_loader.sv','nes_rom_spi.sv'],
  public_sources=p['public_sources']|{str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},no_package=True,adopted=False)
 assert sorted(n for n,h in r['sources'].items() if h!=r['baseline'][n])==r['changed']
 (out/'preparation218.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(changed=r['changed'],files=len(r['sources']))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
