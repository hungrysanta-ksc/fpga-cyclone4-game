# SPDX-License-Identifier: MIT
"""Materialize RUN-only automatic buffers on top of the recorded165 runtime."""
from pathlib import Path
import argparse,json,difflib
from nes_game147 import ROOT,sha
from nes_runtime165 import prepare as runtime_prepare

def prepare(evidence,out):
 prep=runtime_prepare(evidence,out);deltas=[]
 def edit(n,s):
  p=out/n;old=p.read_text(encoding='utf8');assert s!=old,n
  p.write_text(s,encoding='utf8',newline='\n')
  prep['added' if n in prep['added'] else 'changed'][n]=sha(p)
  deltas.extend(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='runtime165/'+n,tofile='runlease165/'+n))
 edit('src/nes_runtime_board165.inc',(ROOT/'src/nes/firmware/nes_runlease165.inc').read_text())
 p=out/'src/nes_menu_diagnostic.c';s=p.read_text(encoding='utf8')
 assert s.count(' char *text=nes_runtime165_log_buffer();FIL log;UINT written=0;')==1
 s=s.replace(' char *text=nes_runtime165_log_buffer();FIL log;UINT written=0;',' char text[4096];FIL log;UINT written=0;').replace('extern char *nes_runtime165_log_buffer(void);\n','')
 edit('src/nes_menu_diagnostic.c',s)
 prep.update(parent_preparation_sha256=sha(out/'preparation-runtime165.json'),scope='RUN-only automatic workspace; noinline function frees33952B before STOP/log/menu. Full stack and coupled client tests required before hardware.')
 (out/'preparation-runlease165.json').write_text(json.dumps(prep,indent=2)+'\n')
 (out/'changes-runlease165.diff').write_text(''.join(deltas),encoding='utf8')
 return prep
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();r=prepare(a.evidence,a.out);print(json.dumps(dict(copied=len(r['copied']),changed=len(r['changed']),added=len(r['added']))))
