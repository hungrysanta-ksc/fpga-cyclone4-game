# SPDX-License-Identifier: MIT
"""Same-edge 32bit epoch as eight local nibbles with registered all-ones flags."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_board204 import ROOT,BASE,sha,replace

def transform(s):
 s=replace(s," wire [31:0] next_serial=serial+32'd1;",''' // Eight cached nibble predicates move wide carry/limit recognition off
 // the serial->Gray CE path. Flags always describe the CURRENT serial.
 // No pipeline delay: every BEGIN still publishes the incremented ID here.
 (* preserve *) reg [7:0] all_ones;
 wire [31:0] next_serial;
 wire [7:0] next_all_ones;
 genvar group217;
 generate for(group217=0;group217<8;group217=group217+1)begin: epoch_group217
  wire carry_in;
  if(group217==0)assign carry_in=1'b1;
  else assign carry_in=&all_ones[group217-1:0];
  assign next_serial[group217*4+:4]=serial[group217*4+:4]+{3'b0,carry_in};
  assign next_all_ones[group217]=carry_in ? (serial[group217*4+:4]==4'he) : all_ones[group217];
 end endgenerate''')
 s=replace(s,'serial<=0;gray<=0;exhausted<=0;','serial<=0;gray<=0;exhausted<=0;all_ones<=0;')
 s=replace(s,"if(serial==32'hffffffff)", 'if(&all_ones)')
 return replace(s,'else begin serial<=next_serial;gray<=next_serial^(next_serial>>1);end','else begin serial<=next_serial;gray<=next_serial^(next_serial>>1);all_ones<=next_all_ones;end')

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
