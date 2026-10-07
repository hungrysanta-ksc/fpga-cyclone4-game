# SPDX-License-Identifier: MIT
"""Actual C command-to-write-start edge probe; ideal GPIO/card, no wall timing."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
from nes_diag_recovery_checks import function
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False);out=a.out.resolve();raw=a.source.read_text()
 # Full functions preserved, including notices. The host stops at the first
 # sampled DATA start, before payload/CRC/busy; those paths are not qualified.
 names=['wiggle_fast_pos','wiggle_fast_neg','wiggle_fast_neg1','wiggle_fast_pos1','send_command_fast','send_datablock']
 functions=[]
 for n in names:
  import re
  match=re.search(r'^(?:static inline void|int|void) '+n+r'\(',raw,re.M);assert match,n
  functions.append(function(raw[match.start():],n))
 (out/'functions.inc').write_text(raw[:raw.index('#include')]+''.join(functions),encoding='utf-8',newline='\n')
 shutil.copy2(a.source,out/'input-sdnative.c');shutil.copy2(__file__,out/'executed-driver.py')
 shutil.copy2(ROOT/'tests/nes-functional/offline_sd075_host.c',out/'host.c')
 with (out/'compile.log').open('wb') as f:subprocess.run([str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-error=implicit-fallthrough','host.c','-o','probe.exe'],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
 with (out/'run.log').open('wb') as f:r=subprocess.run([str(out/'probe.exe')],stdout=f,stderr=subprocess.STDOUT,timeout=30)
 text=(out/'run.log').read_text();assert r.returncode==0 and 'PASS075 edge_cases=32' in text,text
 result=dict(source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),edge_cases=32,current_cmd24_end_to_start_edges=2,extra_eight_clocks_end_to_start_edges=10,physical=False,scope='command response through first DATA start only; ideal card/GPIO, barriers have no host timing')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(text)
if __name__=='__main__':main()
