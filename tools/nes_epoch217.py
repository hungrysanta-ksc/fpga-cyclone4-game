# SPDX-License-Identifier: MIT
"""Parallel prefix increment and direct next-Gray equations; no new epoch state."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_board204 import ROOT,BASE,sha,replace

def transform(s):
 s=replace(s," wire [31:0] next_serial=serial+32'd1;",''' // Carry into bit i is the reduction of lower OLD serial bits.
 // Gray(i)=serial(i+1)^serial(i); after increment its toggle is
 // carry(i)^carry(i+1) = carry(i)&!serial(i). Avoid an adder->XOR chain.
 wire [31:0] next_serial,next_gray;
 assign next_serial[0]=!serial[0];
 assign next_gray[0]=serial[1]^serial[0]^!serial[0];
 genvar epoch_bit;
 generate for(epoch_bit=1;epoch_bit<32;epoch_bit=epoch_bit+1)begin: epoch_increment217
  wire carry_in=&serial[epoch_bit-1:0];
  assign next_serial[epoch_bit]=serial[epoch_bit]^carry_in;
  if(epoch_bit<31)begin: middle
   assign next_gray[epoch_bit]=serial[epoch_bit+1]^serial[epoch_bit]^(carry_in&!serial[epoch_bit]);
  end else begin: top
   assign next_gray[epoch_bit]=serial[epoch_bit]^carry_in;
  end
 end endgenerate''')
 return replace(s,'gray<=next_serial^(next_serial>>1);','gray<=next_gray;')

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
