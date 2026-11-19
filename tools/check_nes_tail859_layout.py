"""Exercise every raw width and each refused submission in the linked sender's C source."""
import argparse
import json
from pathlib import Path
import subprocess

from prepare_nes_tail859 import ROOT


def check(src,out,cc):
    text=(src/'nes_native_sink165.c').read_text()
    start=text.index('  const uint8_t *tables=')
    end=text.index('  size[5]=(uint16_t)(offset+249);',start)+len('  size[5]=(uint16_t)(offset+249);')
    block=text[start:end]
    harness=r'''
#include "nes_native_video165.h"
#include <assert.h>
#include <string.h>
static struct nes_native_video165 plan, original;
static unsigned cursor, calls, refuse;
static uint8_t expected[3418];
static bool emit(unsigned section,unsigned at,const uint8_t *data,unsigned n){
 assert(section==5 && at==cursor && n && at+n<=sizeof expected);
 if (++calls==refuse) return false;
 assert(!memcmp(data,expected+at,n));
 cursor+=n;
 return true;
}
static bool packet(void *s,unsigned op,unsigned section,unsigned at,const uint8_t *data,unsigned n){
 assert(op==2 && n<=240);
 return emit(section,at,data,n);
}
static bool span(void *s,unsigned section,unsigned at,const uint8_t *data,unsigned n){
 return emit(section,at,data,n);
}
static bool send(void){
 struct nes_native_video165 *p=&plan;
 void *s=0;
 const uint8_t *raw=p->patch_count<=2?(uint8_t *)p->bg_keys+4096:p->patch.chr;
 unsigned packed=p->patch_count<=2?p->patch_count*192:2048,offset=1121;
 uint16_t size[6]={0};
 BLOCK
 assert(size[5]==1121+packed+249 && size[5]==cursor);
 return true;
}
int main(void){
 for(unsigned count=1;count<=7;count++){
  for(unsigned i=0;i<sizeof plan;i++)((uint8_t *)&original)[i]=(uint8_t)(i*97+(i>>7)+count);
  original.patch_count=count;
  original.patch.size[0]=1;original.patch.size[1]=21;original.patch.size[2]=81;
  unsigned n=count<=2?count*192:2048;
  const uint8_t *raw=count<=2?(const uint8_t *)original.bg_keys+4096:original.patch.chr;
  memcpy(expected+1121,raw,n);
  unsigned at=1121+n;
  memcpy(expected+at,original.patch.mode[0],81);
  memcpy(expected+at+81,original.patch.mode[1],81);
  memcpy(expected+at+162,original.patch.enable,81);
  memcpy(expected+at+243,original.patch.size,6);
  unsigned total;
  for(refuse=0;;refuse++){
   plan=original;calls=0;cursor=1121;
   bool ok=send();
   assert(ok==(refuse==0));
   if(!refuse)total=calls;else assert(calls==refuse);
   assert(!memcmp(&original.patch,&plan.patch,sizeof plan.patch));
   if(refuse==total)break;
  }
 }
 return 0;
}
'''.replace('BLOCK',block)
    out.mkdir(parents=True,exist_ok=True)
    test=out/'layout.c'
    test.write_text(harness)
    exe=out/'layout.exe'
    subprocess.run([cc,'-std=c11','-O2','-I',src,test,'-o',exe],check=True)
    subprocess.run([exe],check=True)
    (out/'result.json').write_text(json.dumps(dict(patch_counts=list(range(1,8)),
        packed_widths=[192,384,2048],canonical_source_preserved=True,refused_each_submission=True))+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('variant')
    p.add_argument('--cc',type=Path,default=Path('C:/altera_lite/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe'))
    a=p.parse_args()
    check(ROOT/f'link-{a.variant}'/'src',ROOT/f'layout-{a.variant}',a.cc)
