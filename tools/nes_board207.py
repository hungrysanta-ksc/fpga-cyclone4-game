# SPDX-License-Identifier: MIT
"""NES207: local cold-reset release for the96 epoch sampling registers."""
from pathlib import Path
import argparse,json,shutil
from nes_board204 import ROOT,BASE,sha,replace

def epoch(s):
 s=replace(s,'module nes_source_epoch205(','module nes_source_epoch207(')
 s=replace(s,' wire invalid=reset||exhausted', ''' // Cold reset may be released by the memory domain while NES is stopped.
 // Only this release chain sees that deassertion. Keep admission held while
 // the96 sampling registers are still held in their local cold reset.
 wire cold_reset;
 nes_domain_reset124 cold_release(.clk(nes_clk),.raw_reset(reset),.reset(cold_reset));
 wire invalid=reset||cold_reset||exhausted''')
 s=replace(s,''' always @(posedge nes_clk or posedge reset)begin
  if(reset)begin epoch_meta<=0;epoch_sync<=0;previous<=0;end''',''' always @(posedge nes_clk or posedge cold_reset)begin
  if(cold_reset)begin epoch_meta<=0;epoch_sync<=0;previous<=0;end''')
 return s

def prepare(out):
 out=out.resolve();out.mkdir(parents=True,exist_ok=False)
 old=BASE/'probes/nes-board206/source03';p=json.loads((old/'preparation206.json').read_bytes())
 for n,h in p['sources'].items():
  assert sha(old/n)==h,n;(out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,out/n)
 (out/'nes_source_epoch207.sv').write_text(epoch((old/'nes_source_epoch205.sv').read_text()),encoding='utf8',newline='\n')
 for n,a,b in [('nes_spi_boot.sv','nes_source_epoch205 content_lifetime','nes_source_epoch207 content_lifetime'),
               ('board.qsf','SYSTEMVERILOG_FILE nes_source_epoch205.sv','SYSTEMVERILOG_FILE nes_source_epoch207.sv')]:
  f=out/n;f.write_text(replace(f.read_text(),a,b),encoding='utf8',newline='\n')
 names=list(p['sources'])+['nes_source_epoch207.sv']
 result=dict(sources={n:sha(out/n) for n in names},baseline=p['sources'],public_sources={'tools/nes_board207.py':sha(Path(__file__))},
  changed=[n for n in p['sources'] if sha(out/n)!=p['sources'][n]],old_constraints_unchanged=True,no_package=True,adopted=False)
 (out/'preparation207.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(files=len(names),changed=result['changed'])))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
