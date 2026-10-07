# SPDX-License-Identifier: MIT
"""Negative control: delaying capture until BLOCKED loses the first stage."""
from pathlib import Path
import argparse,shutil,subprocess,json
def main():
 p=argparse.ArgumentParser();p.add_argument('--host',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True);a=p.parse_args()
 shutil.copytree(a.host,a.out);out=a.out.resolve();f=out/'nes_diag_platform.c';s=f.read_text()
 old='if(!signal&&(r->error||r->phase==NES_DIAG_BLOCKED))'
 assert s.count(old)==1;s=s.replace(old,'if(!signal&&(r->phase==NES_DIAG_BLOCKED))',1);f.write_text(s,encoding='utf-8',newline='\n')
 with (out/'mutation-compile.log').open('wb') as log:
  subprocess.run([str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-clobbered','-I.','led.c','nes_diag_platform.c','nes_diag_runtime.c','-o','mutant.exe'],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True)
 with (out/'mutation.log').open('wb') as log:r=subprocess.run([str(out/'mutant.exe')],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=30)
 text=(out/'mutation.log').read_text(errors='replace')
 assert r.returncode!=0 and 'nr==e+1&&nw==stage' in text,(r.returncode,text)
 (out/'mutation-result.json').write_text(json.dumps(dict(mutation='capture_only_at_blocked',rejected=True,exit=r.returncode))+'\n')
 print('PASS074 causal late-capture mutation rejected at first-stage pulse assertion')
if __name__=='__main__':main()
