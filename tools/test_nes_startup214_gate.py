# SPDX-License-Identifier: MIT
"""Actual214 gate/formatter: all terminal causes, wrap, bounds and retention."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_runtime213 import ROOT,BASE,sha

CODE=r'''
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <assert.h>
#include <string.h>
#include "nes_budget210.h"
#include "nes_boot214.h"
struct nes_rom_spi_io {int dummy;};
enum {NES_RUNTIME165_SERVICE=2};
static struct {unsigned result;} native_runtime165;
static struct {unsigned screen_stage,screen_error,screen_flags,screen_valid,first_error;} nes_run136;
static unsigned calls,mode;static uint32_t ticks;
static uint32_t getticks(void){return ticks;}
static unsigned get_snes_reset(void){return 0;}
static unsigned fpga_get_done(void){return 1;}
#define BITBAND(a,b) 1
static bool native_service165(void *p){(void)p;if(mode==4){nes_run136.first_error=1;return false;}return true;}
static bool screen146(const struct nes_rom_spi_io *p){
 (void)p;calls++;if(mode!=6)ticks++;
 if(mode==5||(mode==10&&calls==3))return false;
 nes_run136.screen_valid=1;nes_run136.screen_flags=mode==9?7:0;
 nes_run136.screen_stage=mode==0?3:mode==1?(calls>=10?3:2):mode==3?0xe1:mode==7?1:mode==8?2:0;
 return true;
}
#include "nes_boot214.inc"
int main(void){
 struct nes_rom_spi_io io={0};char text[4096];
 unsigned reasons[]={1,1,5,4,2,3,6,5,5,5,3};
 for(mode=0;mode<11;mode++){
  calls=0;ticks=mode==2?UINT32_MAX-100:0;memset(&nes_run136,0,sizeof nes_run136);native_runtime165.result=0;
  bool ok=native_boot172(&io);assert(ok==(mode<2));assert(nes_boot214.reason==reasons[mode]);
  assert(nes_boot214.signals==0x606&&nes_boot214.polls>0);
  if(ok)assert(native_runtime165.result==0&&nes_run136.first_error==0);
  else assert(native_runtime165.result==2&&nes_run136.first_error==(mode==4?1:6));
  if(mode==2)assert(nes_boot214.ticks==500);
  if(mode==6)assert(nes_boot214.polls==65536&&nes_boot214.ticks==0);
  if(mode==9)assert(nes_boot214.first==0x01070000&&nes_boot214.last==0x01070000);
  if(mode==10)assert(nes_boot214.polls==3&&nes_boot214.last==0x01000000);
  struct nes_boot214 before=nes_boot214;nes_budget210_reset();assert(!memcmp(&before,&nes_boot214,sizeof before));
  int n=nes_budget210_format(text,sizeof text);assert(n>0&&n<4096&&strstr(text,"boot_schema=214\n"));
 }
 memset(&nes_budget210,255,sizeof nes_budget210);nes_budget210.open=true;memset(&nes_boot214,255,sizeof nes_boot214);
 int n=nes_budget210_format(text,sizeof text);assert(n>0&&n<4096);assert(nes_budget210_format(text,n)==-1);
 assert(nes_budget210_format(text,n+1)==n);assert(nes_budget210_format(text,32)==-1);
 printf("PASS STARTUP214_GATE cases=11 persistent_bytes=%u format_max=%d\n",(unsigned)sizeof nes_boot214,n);
}
'''
def main():
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False);src=(a.arm/'src').resolve()
    for n in ['nes_boot214.h','nes_boot214.inc']:assert sha(src/n)==sha(ROOT/'src/nes/firmware'/n)
    old=(BASE/'probes/nes-runtime213/arm01/src/nes_menu_diagnostic.c').read_text()
    new=(src/'nes_menu_diagnostic.c').read_text()
    def tail(s):return s[s.index(' if(!persist)return;'):s.index('\nbool nes_menu_diagnostic_run(')]
    assert tail(new).replace('214','213')==tail(old)
    assert sha(src/'nes_native_runtime165.c')==sha(BASE/'probes/nes-runtime213/arm01/src/nes_native_runtime165.c')
    (a.out/'gate.c').write_text(CODE,encoding='utf8')
    gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
    env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
    for name,cmd in [('build',[gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',src,a.out/'gate.c',src/'nes_budget210.c','-o',a.out/'gate.exe']),('run',[a.out/'gate.exe'])]:
        with (a.out/(name+'.log')).open('wb') as f:q=subprocess.run(list(map(str,cmd)),env=env,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        assert q.returncode==0,(a.out/(name+'.log')).read_text(errors='replace')
    r=dict(passed=True,cases=11,persistent_bytes=24,output=(a.out/'run.log').read_text(),unchanged_runtime=True,unchanged_save_tail=True,source_sha256=sha(Path(__file__)),source_pins={n:sha(src/n) for n in ['nes_boot214.h','nes_boot214.inc','nes_budget210.c']})
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
