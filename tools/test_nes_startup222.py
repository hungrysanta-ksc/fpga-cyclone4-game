# SPDX-License-Identifier: MIT
"""Exercise actual222 handoff/boot/cleanup C; optional real bridge SPI replies."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_runtime213 import ROOT,BASE,sha

CODE=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "nes_rom_spi.h"
#include "nes_mcu_loader.h"
#include "nes_run136.h"
#include "nes_native_runtime165.h"
#include "nes_boot214.h"
#include "nes_startup222.h"
#include "nes_plan215.h"
#include "nes_budget210.h"
struct nes_run136_report nes_run136;
struct nes_plan215 nes_plan215;
static unsigned mode,queries,releases,leaves,begins,stops,checks;
static bool reset_held,broken;static uint32_t ticks;
static uint8_t reply[20];static const uint8_t *post_fixture;
static unsigned get_snes_reset(void){return reset_held;}
static unsigned fpga_get_done(void){return 1;}
#define BITBAND(a,b) 1
static uint32_t getticks(void){return ticks;}
static bool nes_cf86_check094(void){if((!reset_held&&!releases)||(reset_held&&releases&&!leaves)){broken=true;reset_held=true;}return !broken;}
static bool nes_cf86_fail094(void){broken=true;reset_held=true;return false;}
static bool nes_display_enter146(void){assert(reset_held&&(nes_startup222.reason==1||nes_startup222.reason==6));releases++;reset_held=false;return true;}
static bool nes_display_leave146(void){assert(!reset_held);leaves++;reset_held=true;return true;}
static bool observe136(const struct nes_rom_spi_io *io,uint32_t *n){
 (void)io;*n=stops?10000:100;nes_run136.flags=stops?1:0;return true;
}
static bool context146(const struct nes_rom_spi_io *io){(void)io;return true;}
static bool screen146(const struct nes_rom_spi_io *io){
 (void)io;if(stops)return true;ticks++;
 if(mode==11)return false;
 nes_run136.screen_valid=1;nes_run136.screen_stage=mode==9?0:mode==10?0xe1:3;
 return true;
}
static bool nes_native165_bulk(const struct nes_rom_spi_io *io,const uint8_t *tx,uint8_t *rx,unsigned n){
 (void)io;assert(reset_held==!releases&&n==20&&tx[0]==0xe0);for(unsigned i=1;i<n;i++)assert(!tx[i]);
 queries++;memcpy(rx,post_fixture&&queries==2?post_fixture:reply,n);
 if(mode==12)reset_held=false;
 if(mode==18&&queries==2)reset_held=true;
 return mode!=6&&!(mode==17&&queries==2);
}
#include "nes_runtime_board165.inc"
bool nes_runtime165_begin(struct nes_native_runtime165 *s,struct nes_native165 *r,
 struct nes_native_video165 *v,const uint16_t p[64],nes_native165_transfer_fn fn,
 uint32_t (*tick)(void *),bool (*service)(void *),void *ctx,uint32_t limit,
 struct nes_resident211 *resident,uint32_t epoch,bool immutable){
 (void)p;(void)fn;(void)tick;(void)service;(void)ctx;
 assert(!reset_held&&nes_boot214.reason==1&&limit==6000&&epoch==123&&immutable);
 begins++;s->receiver=r;s->video=v;s->resident=resident;s->frames=1;s->result=NES_RUNTIME165_DEADLINE;
 nes_run136.first=1;nes_run136.last=100;return true;
}
bool nes_runtime165_step(struct nes_native_runtime165 *s){(void)s;return false;}
static bool nes_checkpoint112(const char *s,uint32_t a,uint32_t b){(void)s;(void)a;(void)b;assert(reset_held);return true;}
static bool nes_rom_verified_start(const struct nes_rom_spi_io *io,uint32_t n){(void)io;assert(reset_held&&n==0x60000);return true;}
void nes_rom_spi_frame(uint8_t *b,uint8_t op,uint32_t n,uint8_t arg){(void)n;(void)arg;memset(b,0,8);b[0]=op;}
bool nes_rom_spi_transfer(const struct nes_rom_spi_io *io,const uint8_t tx[8],uint8_t rx[8]){
 (void)io;memset(rx,0,8);assert(reset_held&&tx[0]==NES_ROM_STOP);stops++;return true;
}
static bool sd_query(const struct nes_rom_spi_io *io,struct nes_rom_spi_status *s){(void)io;s->flags=2;s->count=0x60000;return true;}
static bool ppu154(const struct nes_rom_spi_io *io){(void)io;return true;}
static bool history157(const struct nes_rom_spi_io *io){(void)io;return true;}
static bool pad156(const struct nes_rom_spi_io *io){(void)io;return true;}
// RUN_BODY
static void crc(void){unsigned c=0;for(unsigned i=1;i<19;i++){c^=reply[i];for(unsigned j=0;j<8;j++)c=((c&128)?(c<<1)^7:c<<1)&255;}reply[19]=(uint8_t)c;}
static void setup(void){
 reset_held=true;broken=false;queries=releases=leaves=begins=stops=0;ticks=0;post_fixture=NULL;
 memset(&native_runtime165,0,sizeof native_runtime165);memset(&nes_run136,0,sizeof nes_run136);
 memset(&nes_boot214,255,sizeof nes_boot214);memset(&nes_plan215,255,sizeof nes_plan215);
 memset(&nes_startup222,255,sizeof nes_startup222);memset(reply,0,20);reply[1]=0xf7;crc();
}
int main(int argc,char **argv){
 struct nes_rom_spi_io io={0};
 for(mode=0;mode<19;mode++){
  setup();if(mode==1)memset(reply,0,20);if(mode==2)reply[19]^=1;
  if(mode==3){reply[2]=128;crc();}if(mode==4){reply[4]=1;crc();}
  if(mode==5){reply[7]=1;crc();}if(mode==7)broken=true;
  if(mode==8)reset_held=false;
  if(mode==13){reply[1]=0xf6;crc();}
  uint8_t post[20];
  if(mode>=14){
   if(mode==16){reply[4]=1;crc();}
   memcpy(post,reply,20);if(mode==15)post[19]^=1;
   memset(reply,mode==14?255:0,20);post_fixture=post;
  }
  if(mode==7||mode==8){assert(!native_preflight222(&io)&&!queries&&!releases);checks++;continue;}
  struct nes_mcu_load_report load={0};bool ok=run136(&io,0x60000,&load,123);
  if(mode==0||mode==14){assert(ok&&begins==1&&releases==1&&leaves==1&&stops==1&&load.stop_ok&&nes_run136.passed);}
  else if(mode==9||mode==10){assert(ok&&begins==0&&releases==1&&leaves==1&&stops==1&&nes_run136.first_error==6);assert(nes_boot214.reason==(mode==9?5:4));}
  else if(mode==1){assert(ok&&!begins&&releases==1&&leaves==1&&stops==1&&nes_run136.first_error==8&&nes_startup222.post_reason==6);}
  else if(mode==11||mode==12||mode==18){assert(!ok&&broken&&stops==0&&begins==0);}
  else if(mode>=15){assert(ok&&!begins&&releases==1&&leaves==1&&stops==1&&nes_run136.first_error==8);assert(nes_startup222.post_reason==(mode==15?4:mode==16?5:3));}
  else {assert(ok&&begins==0&&releases==0&&leaves==0&&stops==1&&nes_run136.first_error==7&&nes_boot214.reason==0);}
  assert(queries<=((mode==1||mode>=14)?2u:1u)&&native_io165==NULL);assert(!native_runtime165.receiver&&!native_runtime165.video&&!native_runtime165.resident);
  struct nes_startup222 saved=nes_startup222;nes_budget210_reset();assert(!memcmp(&saved,&nes_startup222,sizeof saved));checks++;
 }
 /* Feed raw20B replies captured from the unchanged real bridge RTL. */
 if(argc==2){FILE *f=fopen(argv[1],"r");assert(f);unsigned expected,v,cases=0;uint8_t raw[5][20];
  while(fscanf(f,"%u",&expected)==1){assert(cases<5);for(unsigned i=0;i<20;i++){assert(fscanf(f,"%x",&v)==1);raw[cases][i]=(uint8_t)v;}cases++;}
  fclose(f);assert(cases==5);
  for(unsigned c=0;c<5;c++){mode=0;setup();memcpy(reply,raw[c],20);if(c==1||c==3)post_fixture=raw[c+1];
   struct nes_mcu_load_report load={0};assert(run136(&io,0x60000,&load,123));assert(begins==(c!=0)&&releases==1&&stops==1);
   if(c==1||c==3)assert(nes_startup222.reason==6&&nes_startup222.post_reason==1&&queries==2);
  }checks+=cases;
 }
 char text[4096];memset(&nes_budget210,255,sizeof nes_budget210);nes_budget210.open=true;
 memset(&nes_startup222,255,sizeof nes_startup222);memset(&nes_boot214,255,sizeof nes_boot214);memset(&nes_plan215,255,sizeof nes_plan215);
 int n=nes_budget210_format(text,sizeof text);assert(n>0&&n<4096&&strstr(text,"startup_schema=222\n"));
 assert(nes_budget210_format(text,n)==-1&&nes_budget210_format(text,n+1)==n);
 printf("PASS STARTUP222 checks=%u max_report=%d preflight_bytes=%u no_retry=1\n",checks,n,(unsigned)sizeof nes_startup222);
}
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--rtl-replies',type=Path);a=p.parse_args()
 d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);src=(a.arm/'src').resolve()
 run=(src/'nes_run136.inc').read_text();body=run[run.index('static bool run136('):]
 (d/'test.c').write_text(CODE.replace('// RUN_BODY',body),encoding='utf8')
 def tail(s):return s[s.index(' if(!persist)return;'):s.index('\nbool nes_menu_diagnostic_run(')]
 assert tail((src/'nes_menu_diagnostic.c').read_text()).replace('222','221')==tail((BASE/'probes/nes-index221/arm01/src/nes_menu_diagnostic.c').read_text())
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
 commands=[('build',[gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',src,d/'test.c',src/'nes_budget210.c','-o',d/'test.exe']),('run',[d/'test.exe',*([a.rtl_replies.resolve()] if a.rtl_replies else [])])]
 for name,args in commands:
  with (d/(name+'.log')).open('wb') as f:q=subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,env=env,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
  assert q.returncode==0,(d/(name+'.log')).read_text(errors='replace')
 r=dict(passed=True,output=(d/'run.log').read_text(),source_pins={n:sha(src/n) for n in ['nes_runtime_board165.inc','nes_run136.inc','nes_boot214.inc','nes_startup222.inc','nes_startup222.h','nes_budget210.c','nes_menu_diagnostic.c']},public_source_sha256=sha(Path(__file__)),rtl_reply_sha256=sha(a.rtl_replies) if a.rtl_replies else None,scope='Actual C handoff/boot/STOP cleanup with mocked platform; optional RTL SPI replies replayed, not live ARM/65816 co-simulation or physical root-cause proof.')
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(r['output'])
if __name__=='__main__':main()
