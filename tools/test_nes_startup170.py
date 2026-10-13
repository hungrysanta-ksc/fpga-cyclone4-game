# SPDX-License-Identifier: MIT
"""Differential packet/guard execution against165; failure/lifetime/buffer checks."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_game147 import ROOT,sha
HARNESS=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "nes_sink_spi165.h"
#include "nes_sink_io170.h"
bool baseline_exchange(void *,const uint8_t *,unsigned,uint8_t *);
struct ctx {unsigned calls,guards,polls,ready,fail_guard,fail_call,corrupt_at,mode,expected;uint32_t hash;};
static uint8_t crc(uint8_t c,uint8_t b){c^=b;for(unsigned i=0;i<8;i++)c=(uint8_t)(c&128?(c<<1)^7:c<<1);return c;}
static bool guard(void *v){struct ctx *c=v;c->guards++;c->hash=c->hash*33+7;
 if(c->guards==c->fail_guard){c->expected=c->guards==1?2:c->guards==2?6:8;return false;}return true;}
static bool transfer(void *v,const uint8_t *tx,uint8_t *rx,unsigned n){
 struct ctx *c=v;c->calls++;c->hash=c->hash*33+n;for(unsigned i=0;i<n;i++)c->hash=c->hash*33+tx[i];
 if(c->calls>=3)c->polls++;
 if(c->calls==c->fail_call){c->expected=c->calls==1?3:c->calls==2?7:9;return false;}
 memset(rx,0,n);if(tx[0]==0xe1)return true;
 rx[1]=0xf6;rx[2]=c->calls==1?0:1;
 if(c->polls&&c->polls>=c->ready){rx[2]=2;for(unsigned i=3;i<15;i++)rx[i]=(uint8_t)(i*17);}
 if(c->calls==c->corrupt_at){
  if(c->mode==1)rx[1]=0xd6;
  if(c->mode==3)rx[2]=3;
  if(c->mode==4)rx[2]=1;
  c->expected=(c->calls==1?(c->mode==4?5:4):10)|128;
 }
 for(unsigned i=1;i<15;i++)rx[15]=crc(rx[15],rx[i]);
 if(c->calls==c->corrupt_at&&c->mode==2)rx[15]^=1;
 return true;
}
static unsigned cases;
static void run(unsigned n,unsigned limit,unsigned ready,unsigned fg,unsigned fc,unsigned at,unsigned mode){
 uint8_t p[256]={1},a[12],b[12];p[12]=(uint8_t)(n-16);p[13]=(uint8_t)((n-16)>>8);
 for(unsigned i=16;i<n;i++)p[i]=(uint8_t)(i*29);
 memset(a,0x5a,sizeof a);memcpy(b,a,sizeof a);
 struct ctx x={.ready=ready,.fail_guard=fg,.fail_call=fc,.corrupt_at=at,.mode=mode},y=x;
 struct nes_sink_spi165 s={transfer,&x,guard,limit},t=s;t.ctx=&y;
 bool old=baseline_exchange(&s,p,n,a);memset(&nes_sink_io170,0,sizeof nes_sink_io170);
 bool now=nes_sink_spi165_exchange(&t,p,n,b);
 assert(old==now&&memcmp(a,b,12)==0&&memcmp(&x,&y,sizeof x)==0);
 if(now)assert(nes_sink_io170.reason==0);
 else{
  assert(nes_sink_io170.reason==(y.expected?y.expected:139));
  assert(nes_sink_io170.polls==y.polls);
  if(nes_sink_io170.reason&128){uint8_t c=0;for(unsigned i=0;i<14;i++)c=crc(c,nes_sink_io170.status[i]);
   assert((c!=nes_sink_io170.status[14])==(at&&mode==2));
  }else for(unsigned i=0;i<15;i++)assert(nes_sink_io170.status[i]==0);
  struct nes_sink_io170 first=nes_sink_io170;assert(!nes_sink_io170_fail(1,99,NULL));assert(!memcmp(&first,&nes_sink_io170,sizeof first));
 }
 cases++;
}
int main(void){
 for(unsigned n=16;n<=256;n++)run(n,8,3,0,0,0,0);
 for(unsigned i=1;i<=7;i++){run(16,8,9,i,0,0,0);run(16,8,9,0,i,0,0);}
 for(unsigned m=1;m<=4;m++){run(16,8,9,0,0,1,m);if(m!=4){run(16,8,9,0,0,3,m);run(16,8,9,0,0,5,m);}}
 run(16,65536,65536,0,0,0,0);run(16,65536,65537,0,0,0,0);assert(nes_sink_io170.polls==65536&&nes_sink_io170.reason==139);
 memset(&nes_sink_io170,0,sizeof nes_sink_io170);uint8_t ack[12];assert(!nes_sink_spi165_exchange(NULL,NULL,0,ack));assert(nes_sink_io170.reason==1);
 char b[80];memset(b,0x5a,sizeof b);int n=nes_sink_io170_format(b,sizeof b);assert(n==54&&b[n]==0&&b[n+1]==0x5a);
 char small[54];memset(small,0x5a,sizeof small);assert(nes_sink_io170_format(small,54)==-1);for(unsigned i=0;i<54;i++)assert(small[i]==0x5a);
 assert(nes_sink_io170_format(NULL,100)==-1);
 printf("PASS differential=%u packet_lengths=241 poll_limit=65536 first_failure_latch=1 format_bounds=1\n",cases);
}
'''
def main():
 p=argparse.ArgumentParser()
 for n in ['arm','prior','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 (a.out/'harness.c').write_text(HARNESS,encoding='utf8');env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','')
 def run(args,name):
  with (a.out/(name+'.log')).open('wb') as f:q=subprocess.run([str(x) for x in args],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=90)
  assert q.returncode==0,(a.out/(name+'.log')).read_text(errors='replace')
 src=a.arm/'src';base=[a.gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',src]
 run(base+['-Dnes_sink_spi165_exchange=baseline_exchange','-c',a.prior/'src/nes_sink_spi165.c','-o',a.out/'baseline.o'],'baseline')
 run(base+[a.out/'harness.c',src/'nes_sink_spi165.c',src/'nes_sink_io170.c',a.out/'baseline.o','-o',a.out/'test.exe'],'build')
 run([a.out/'test.exe'],'run')
 r={'passed':True,'output':(a.out/'run.log').read_text(),'public_sources':{n:sha(ROOT/n) for n in ['tools/test_nes_startup170.py','src/nes/firmware/nes_sink_spi170.c','src/nes/firmware/nes_sink_io170.c','src/nes/firmware/nes_sink_io170.h']},'scope':'Actual old/new C exchange and callbacks, same bytes/order/guard/return. Scripted SPI status, not physical bus.'}
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(r['output'])
if __name__=='__main__':main()
