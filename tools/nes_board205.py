# SPDX-License-Identifier: MIT
"""Local epoch admission + streaming into existing unpublished bulk tile RAM."""
from pathlib import Path
import argparse,json,shutil
from nes_board204 import ROOT,BASE,sha,replace

def prepare(out):
 out=out.resolve();out.mkdir(parents=True,exist_ok=False)
 old=BASE/'probes/nes-board204/source01';p=json.loads((old/'preparation204.json').read_bytes())
 for n,h in p['sources'].items():
  assert sha(old/n)==h,n;(out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,out/n)
 public={}
 for n in ['nes_source_epoch205.sv','nes_tile205.sv']:
  src=ROOT/'src/nes/rtl'/n;shutil.copyfile(src,out/n);public[src.relative_to(ROOT).as_posix()]=sha(src)
 for n,a,b in [('nes_spi_boot.sv','nes_source_epoch204 content_lifetime','nes_source_epoch205 content_lifetime'),
               ('nes_source_tile192.sv','nes_tile191 #','nes_tile205 #')]:
  f=out/n;f.write_text(replace(f.read_text(),a,b),encoding='utf8',newline='\n')
 f=out/'board.qsf';s=f.read_text()
 for a,b in [('nes_source_epoch204.sv','nes_source_epoch205.sv'),('nes_tile191.sv','nes_tile205.sv')]:
  s=replace(s,'SYSTEMVERILOG_FILE '+a,'SYSTEMVERILOG_FILE '+b)
 f.write_text(s,encoding='utf8',newline='\n')
 names=list(p['sources'])+['nes_source_epoch205.sv','nes_tile205.sv']
 public['tools/nes_board205.py']=sha(Path(__file__))
 result=dict(sources={n:sha(out/n) for n in names},baseline=p['sources'],public_sources=public,
  changed=[n for n in p['sources'] if sha(out/n)!=p['sources'][n]],
  old_unused_sources=['nes_source_epoch204.sv','nes_tile191.sv'],old_constraints_unchanged=True,
  no_package=True,adopted=False)
 (out/'preparation205.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(files=len(names),changed=result['changed'])))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
