# SPDX-License-Identifier: MIT
"""Full compile-only tree; no hardware identity/package approval."""
from pathlib import Path
import argparse,json
from nes_runtime202 import ROOT,BASE,sha
from nes_board181 import copy_pins
from nes_clip178 import replace

def prepare(candidate,out):
 prior=BASE/'probes/nes-paired186/arm01'
 p=json.loads((prior/'preparation-paired186.json').read_bytes());pins=p['copied']|p['changed']|p['added']
 copy_pins(prior,out,pins);changed={};added={}
 prep=json.loads((candidate/'preparation202.json').read_bytes())
 for n,h in prep['generated'].items():
  if not n.endswith(('.c','.h','.inc')):continue
  assert sha(candidate/n)==h,n
  name='src/'+n;(out/name).write_bytes((candidate/n).read_bytes())
  (changed if name in pins else added)[name]=h
 f=out/'src/Makefile';s=replace(f.read_text(),'nes_native_runtime165.c\n','nes_native_runtime165.c nes_plan191.c nes_plan_service200.c\n')
 f.write_text(s,encoding='utf8',newline='\n');changed['src/Makefile']=sha(f)
 # Keep manual loader labels for compile comparison, but mark binary unambiguously.
 f=out/'src/VERSION';s=f.read_text();assert 'NES-GAME186-DEV' in s
 f.write_text(s.replace('NES-GAME186-DEV','NES-RUN202-DEV'),encoding='utf8',newline='\n');changed['src/VERSION']=sha(f)
 r=dict(copied=pins,changed=changed,added=added,hardware_package=False,paired_board_ready=False)
 (out/'preparation-runtime202.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(copied=len(pins),changed=len(changed),added=len(added))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.candidate,a.out)
