# SPDX-License-Identifier: MIT
"""Prepare207 board with216 execution-only tile watchdog; no timing waiver."""
from pathlib import Path
import argparse,json,shutil
from nes_board204 import ROOT,BASE,sha

def prepare(out):
 out=out.resolve();out.mkdir(parents=True,exist_ok=False)
 old=BASE/'probes/nes-board207/source02';p=json.loads((old/'preparation207.json').read_bytes())
 for n,h in p['sources'].items():
  assert sha(old/n)==h,n;(out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,out/n)
 public=ROOT/'src/nes/rtl/nes_tile205.sv';shutil.copyfile(public,out/public.name)
 result=dict(sources={n:sha(out/n) for n in p['sources']},baseline=p['sources'],
  public_sources={str(public.relative_to(ROOT)):sha(public),str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},
  changed=[n for n in p['sources'] if sha(out/n)!=p['sources'][n]],
  old_constraints_unchanged=True,no_package=True,adopted=False)
 assert result['changed']==['nes_tile205.sv']
 (out/'preparation216.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(changed=result['changed'],files=len(result['sources']))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
