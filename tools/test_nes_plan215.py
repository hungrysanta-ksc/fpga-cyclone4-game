# SPDX-License-Identifier: MIT
"""Differential old/new service predicates plus retained log bounds; mocked SPI."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_runtime213 import ROOT,BASE,sha
CODE=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "nes_plan_service200.h"
#include "nes_plan215.h"
#include "nes_budget210.h"
#include "nes_boot214.h"
bool old_emit(void*,const struct nes_plan191*);
bool old_finish(struct nes_plan200*);
bool old_retire(struct nes_plan200*);
static unsigned calls,target,byte_at,bit_at,recrc,statuses,accepted,checks;
static bool ended;
static uint8_t failed[20];
static uint8_t crc(const uint8_t*b,unsigned n){uint8_t c=0;while(n--){c^=*b++;for(unsigned i=0;i<8;i++)c=(uint8_t)(c&128?(c<<1)^7:c<<1);}return c;}
static bool guard(void*x){(void)x;return true;}
bool nes_sink195_bulk(struct nes_native_sink165*s,const uint8_t*d){(void)s;(void)d;return true;}
static bool transfer(void*x,const uint8_t*tx,uint8_t*rx,unsigned n){
 (void)x;unsigned cmd=tx[0];calls++;memset(rx,0,n);
 if(cmd==0xe9){accepted++;ended=true;}
 else if(cmd==0xea){accepted=0;ended=false;}
 else {assert(cmd==0xe8&&n==20);statuses++;rx[1]=0xd7;rx[2]=4;rx[3]=ended?2:1;rx[4]=(uint8_t)(accepted>>8);rx[5]=(uint8_t)accepted;rx[19]=crc(rx+1,18);
  if(statuses==target){rx[byte_at]^=(uint8_t)(1u<<bit_at);if(recrc)rx[19]=crc(rx+1,18);memcpy(failed,rx,20);}
 }return true;
}
struct outcome {unsigned error,sent,calls;bool ok;};
static struct outcome trial(bool old){
 struct nes_native_sink165 s={0};struct nes_plan200 p={0};struct nes_plan191 q={0};
 s.state=NES_SINK165_BUILD;s.generation=69;p.sink=&s;p.guard=guard;p.transfer=transfer;p.poll_limit=4;
 q.kind=2;q.generation=69;for(unsigned i=0;i<8;i++)q.alt[i]=65535;
 statuses=accepted=calls=0;ended=false;
 bool ok=(old?old_emit:nes_plan200_emit)(&p,&q)&&(old?old_finish:nes_plan200_finish)(&p);
 if(ok){s.state=NES_SINK165_IDLE;s.displayed=true;s.last_generation=69;ok=(old?old_retire:nes_plan200_retire)(&p);}
 return (struct outcome){p.error,p.sent,calls,ok};
}
int main(void){
 for(target=0;target<=4;target++)for(byte_at=0;byte_at<20;byte_at++)for(bit_at=0;bit_at<8;bit_at++)for(recrc=0;recrc<2;recrc++){
  struct outcome a=trial(true);memset(&nes_plan215,0,sizeof nes_plan215);struct outcome b=trial(false);
  assert(a.error==b.error&&a.sent==b.sent&&a.calls==b.calls&&a.ok==b.ok);
  if(b.error==4){assert(nes_plan215.valid&&nes_plan215.reason&&nes_plan215.phase>=1&&nes_plan215.phase<=4);assert(!memcmp(nes_plan215.reply,failed,20));
   struct nes_plan215 kept=nes_plan215;nes_budget210_reset();assert(!memcmp(&kept,&nes_plan215,sizeof kept));
   unsigned saved_target=target,saved_byte=byte_at,saved_bit=bit_at,saved_crc=recrc;
   target=1;byte_at=1;bit_at=0;recrc=1;(void)trial(false);
   target=saved_target;byte_at=saved_byte;bit_at=saved_bit;recrc=saved_crc;
   assert(!memcmp(&kept,&nes_plan215,sizeof kept));
  }else assert(!nes_plan215.valid);
  checks++;
 }
 char text[4096];memset(&nes_budget210,255,sizeof nes_budget210);nes_budget210.open=true;memset(&nes_boot214,255,sizeof nes_boot214);memset(&nes_plan215,255,sizeof nes_plan215);
 int n=nes_budget210_format(text,sizeof text);assert(n>0&&n<4096);assert(strstr(text,"plan_reply_hex=ffffffffffffffffffffffffffffffffffffffff\n"));
 assert(nes_budget210_format(text,n)==-1&&nes_budget210_format(text,n+1)==n&&nes_budget210_format(text,32)==-1);
 printf("PASS PLAN215 checks=%u retained_bytes=%u format_max=%d\n",checks,(unsigned)sizeof nes_plan215,n);
}
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False);src=(a.arm/'src').resolve()
 (a.out/'host.c').write_text(CODE,encoding='utf8');gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
 common=[gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',src]
 old=BASE/'probes/nes-startup214/arm02/src/nes_plan_service200.c'
 commands=[('old',common+['-Dnes_plan200_emit=old_emit','-Dnes_plan200_finish=old_finish','-Dnes_plan200_retire=old_retire','-c',old,'-o',a.out/'old.o']),('build',common+[a.out/'host.c',a.out/'old.o',src/'nes_plan_service200.c',src/'nes_budget210.c','-o',a.out/'host.exe']),('run',[a.out/'host.exe'])]
 for name,cmd in commands:
  with (a.out/(name+'.log')).open('wb') as f:r=subprocess.run(list(map(str,cmd)),env=env,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(a.out/(name+'.log')).read_text(errors='replace')
 result=dict(passed=True,output=(a.out/'run.log').read_text(),source_pins={n:sha(src/n) for n in ['nes_plan_service200.c','nes_plan215.h','nes_budget210.c']},old_sha=sha(old),public_sha=sha(Path(__file__)),scope=__doc__)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
