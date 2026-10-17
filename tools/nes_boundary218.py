# SPDX-License-Identifier: MIT
"""Maintain the SPI last-bit predicate without changing any receive edge."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_board204 import ROOT,BASE,sha,replace

def transform(s):
 s=replace(s,' reg [2:0] bit_count;', ''' reg [2:0] bit_count;
 // Same-edge invariant: byte_last == (bit_count == 7). Predecode the next
 // count on the preceding SPI bit, not on the command/offset capture edge.
 reg byte_last;
 always @(posedge mem_clk or posedge reset)begin
  if(reset)byte_last<=0;
  else if(ss_sync[1])byte_last<=0;
  else if(sck_sync[1] && !sck_previous)byte_last<=bit_count==6;
 end''')
 s=replace(s,'!sck_previous && bit_count==7 && byte_count==0','!sck_previous && byte_last && byte_count==0')
 return replace(s,'if(bit_count==7)begin','if(byte_last)begin')

def prepare(out):
 old=BASE/'probes/nes-loader217/source04';p=json.loads((old/'preparation217.json').read_bytes())
 out.mkdir(parents=True,exist_ok=False)
 for n,h in p['sources'].items():
  assert sha(old/n)==h,n
  (out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,out/n)
 before=(old/'nes_rom_spi.sv').read_text();after=transform(before)
 (out/'nes_rom_spi.sv').write_text(after,encoding='utf8',newline='\n')
 (out/'boundary.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True))),encoding='utf8')
 r=dict(sources={n:sha(out/n) for n in p['sources']},baseline=p['sources'],changed=['nes_rom_spi.sv'],
  public_sources=p['public_sources']|{str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},no_package=True,adopted=False)
 assert [n for n,h in r['sources'].items() if h!=r['baseline'][n]]==r['changed']
 (out/'preparation218.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(changed=r['changed'],files=len(r['sources']))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
