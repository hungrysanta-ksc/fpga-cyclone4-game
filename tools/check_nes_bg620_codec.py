# SPDX-License-Identifier: MIT
"""Differential test of old/new C plan encoders, including rejected records."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from nes_raw506 import sha


def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    for flag,src in [('before',a.base),('after',a.trial)]:
        (a.out/f'{flag}.c').write_text(f'''#include "nes_plan_wire199.h"
unsigned {flag}(const struct nes_plan191 *q, uint8_t out[32]){{return nes_plan199_encode(q,out);}}
''')
        subprocess.run([str(a.gcc),'-std=c99','-Os','-I',os.path.relpath(src,a.out),'-c',f'{flag}.c'],cwd=a.out,check=True)
    (a.out/'check.c').write_text('''#include <stdio.h>
#include <string.h>
#include "nes_plan191.h"
unsigned before(const struct nes_plan191*,uint8_t*),after(const struct nes_plan191*,uint8_t*);
static unsigned lengths[33];
static int check(struct nes_plan191 q){
 uint8_t left[32],right[32];
 unsigned a=before(&q,left),b=after(&q,right);
 if(a>32 || a!=b || memcmp(left,right,a))return 0;
 lengths[a]++;return 1;
}
int main(void){
 for(unsigned k=0;k<5;k++)for(unsigned val=0;val<256;val++){
  struct nes_plan191 q={0};q.generation=65535;q.kind=k;
  q.slot=k<2?1:0;q.mask=k<2?255:0;q.tag=k<2?8191:0;
  memset(q.alt,255,sizeof q.alt);
  for(unsigned j=0;j<16;j++)q.row[j]=k<2?j/2:0;
  if(!check(q))return 1;
  struct nes_plan191 p=q;p.mask=val;if(!check(p))return 2;
  p=q;p.slot=val==255?1024:val*4;if(!check(p))return 3;
  p=q;p.tag=val==255?8192:32*val;if(!check(p))return 4;
  for(unsigned j=0;j<16;j++){p=q;p.row[j]=val;if(!check(p))return 5;}
  for(unsigned j=0;j<8;j++){
   if(val&(1u<<j))q.alt[j]=j+3;
  }
  if(!check(q))return 6;
  p=q;p.alt[val%8]=8192;if(!check(p))return 7;
 }
 for(unsigned i=0;i<=32;i++)printf("%u ",lengths[i]);
 return 0;
}
''')
    subprocess.run([str(a.gcc),'-std=c99','-Os','-I',os.path.relpath(a.trial,a.out),'check.c','before.o','after.o','-o','check.exe'],cwd=a.out,check=True)
    counts=list(map(int,subprocess.check_output([str((a.out/'check.exe').resolve())],text=True).split()))
    assert all(counts[i] for i in (0,3,7,8,*range(16,33,2)))
    (a.out/'result.json').write_text(json.dumps(dict(cases=sum(counts),by_length=counts,reference=sha(a.base/'nes_plan_wire199.h'),
        candidate=sha(a.trial/'nes_plan_wire199.h')),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','trial','gcc','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
