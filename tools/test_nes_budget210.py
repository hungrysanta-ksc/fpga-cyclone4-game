# SPDX-License-Identifier: MIT
"""Changed C only: replay archived actual203 exporter traces, no new RTL run.
Checks reference pixels,9 real RUN frames/6 terminal paths, sorted lookup,
model false-hit boundaries, accounting, bounded post-STOP formatter.
"""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_budget210 import ROOT,BASE,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 prior=BASE/'probes/nes-metadata203/test04';pins={}
 for name in ['host203.c','reference203.c','reference203.h']+[f'scene{i}.wire' for i in range(11)]:
  f=prior/name;shutil.copyfile(f,a.out/name);pins[str(f.relative_to(BASE))]=sha(f)
 for f in (a.arm/'src').iterdir():
  if f.name.startswith('nes_') and f.suffix in ('.c','.h','.inc'):shutil.copyfile(f,a.out/f.name)
 host=(a.out/'host203.c').read_text()
 host=host.replace('#include "nes_native_runtime165.h"','#include "nes_native_runtime165.h"\n#include "nes_budget210.h"')
 host=host.replace('static void init(void){','static struct nes_budget210_cache model_cache;\nstatic void init(void){')
 host=host.replace('runtime.plan.poll_limit=16;','runtime.plan.poll_limit=16;nes_budget210_attach(&model_cache);')
 needle=' assert(services>wire_calls&&!inside);'
 at=host.index(needle)
 host=host[:at]+''' {
  unsigned completed=0,bytes=0;
  for(unsigned b=0;b<12;b++){
   completed+=nes_budget210.bins[b][B210_FRAMES];
   for(unsigned f=B210_INGRESS;f<=B210_OTHER;f++)bytes+=nes_budget210.bins[b][f];
  }
  assert(completed==runtime.frames&&bytes==runtime.wire_bytes);
  assert(!nes_budget210.open&&!nes_budget210.failed_transfers);
 }
'''+host[at:]
 (a.out/'host203.c').write_text(host,encoding='utf8')
 # Same complete callbacks/pixels on the frozen normal+fault fixtures.
 sources=['host203.c','reference203.c','nes_native_runtime165.c','nes_native165.c','nes_trace166.c','nes_plan191.c','nes_plan_service200.c','nes_native_sink165.c','nes_sink_trace168.c','nes_sink_window184.c','nes_budget210.c']
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
 env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
 def run(args,name):
  with (a.out/(name+'.log')).open('wb') as log:r=subprocess.run(list(map(str,args)),cwd=a.out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
  s=(a.out/(name+'.log')).read_text(errors='replace');assert r.returncode==0,s[-6000:];return s
 run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2',*sources,'-o','host.exe'],'build')
 normal=run([a.out/'host.exe'],'host');assert 'frames=9 ' in normal and normal.count('PASS METADATA203 fault=')==6
 # Include planner in one TU to exercise the actual static lookup exhaustively.
 unit=r'''
#include "nes_plan191.c"
#include "nes_budget210.h"
#include <assert.h>
#include <stdio.h>
static struct nes_native165 input;
static struct nes_native_video165 output;
static unsigned calls;
static bool emit(void *ctx,const struct nes_plan191 *q){(void)ctx;(void)q;calls++;return true;}
int main(void){
 unsigned checks=0;
 for(unsigned n=1;n<=512;n*=2){
  input.ntiles=(uint16_t)n;
  for(unsigned i=0;i<n;i++){input.tiles[i].tag=(uint16_t)(i*16);input.tiles[i].kind=(uint8_t)(1+i%3);}
  for(unsigned tag=0;tag<8192;tag++)for(unsigned k=1;k<=2;k++){
   const struct nes_native165_tile *ref=NULL;
   for(unsigned i=0;i<n;i++)if(input.tiles[i].tag==tag&&(input.tiles[i].kind&k)){ref=&input.tiles[i];break;}
   assert(tile(&input,tag,k)==ref);checks++;
  }
 }
 input.state=NES_NATIVE165_COMMITTED;input.counts[0]=33;input.counts[1]=224;input.counts[4]=224;input.counts[5]=32;
 uint16_t lut[64]={0};input.tiles[1].tag=0;
 assert(!nes_native_video191_plan(&input,lut,&output,false,emit,NULL)&&!calls&&output.error==6);
 struct nes_plan191 q={0};q.mask=255;for(unsigned i=0;i<8;i++){q.alt[i]=65535;q.row[i*2]=q.row[i*2+1]=(uint8_t)i;}
 struct nes_budget210_cache cache;
 nes_budget210_reset();nes_budget210_attach(&cache);nes_budget210_frame(0);nes_budget210_plan(&q);nes_budget210_plan(&q);
 assert(nes_budget210.bins[0][B210_REUSE]==0);
 nes_budget210_display(10,&output);nes_budget210_frame(500);nes_budget210_plan(&q);
 assert(nes_budget210.bins[1][B210_REUSE]==16&&nes_budget210.bins[1][B210_REUSE_PLAN]==7);
 q.alt[0]=1;nes_budget210_plan(&q);assert(nes_budget210.bins[1][B210_COMPLEX]==16);
 q.alt[0]=65535;q.row[0]=7;nes_budget210_plan(&q);assert(nes_budget210.bins[1][B210_REUSE]==16);
 nes_budget210.serial=65535;nes_budget210.open=false;nes_budget210_frame(6000);nes_budget210_plan(&q);
 assert(nes_budget210.serial==1&&nes_budget210.bins[11][B210_REUSE]==0);
 nes_budget210_wire(0xe9,248,true);nes_budget210_wire(0xd1,15,false);
 assert(nes_budget210.bins[11][B210_E9]==248&&nes_budget210.failed_transfers==1);
 nes_budget210_detach();assert(!nes_budget210.cache);
 /* Force a real direct-map hash collision; no false positive and eviction
  * cannot be reported as persistent residency. */
 q.row[0]=0;q.tag=0;nes_budget210_reset();nes_budget210_attach(&cache);nes_budget210_frame(0);nes_budget210_plan(&q);
 unsigned slot=0;while(!cache.seen[slot])slot++;
 unsigned collision=0;
 for(unsigned tag=1;tag<8192&&!collision;tag++){
  nes_budget210_reset();nes_budget210_attach(&cache);nes_budget210_frame(0);q.tag=(uint16_t)tag;nes_budget210_plan(&q);
  if(cache.seen[slot])collision=tag;
 }
 assert(collision);nes_budget210_reset();nes_budget210_attach(&cache);nes_budget210_frame(0);q.tag=0;nes_budget210_plan(&q);
 nes_budget210_display(1,&output);nes_budget210_frame(2);q.tag=(uint16_t)collision;nes_budget210_plan(&q);
 nes_budget210_display(3,&output);nes_budget210_frame(4);q.tag=0;nes_budget210_plan(&q);assert(!nes_budget210.bins[0][B210_REUSE]);
 nes_budget210_reset();assert(!nes_budget210.cache&&!nes_budget210.bins[0][B210_FRAMES]);
 memset(&nes_budget210,255,sizeof nes_budget210);nes_budget210.open=true;
 char text[4096];int n=nes_budget210_format(text,sizeof text);assert(n>0&&n<4096);
 assert(nes_budget210_format(text,32)==-1);
 printf("PASS BUDGET210 lookup_checks=%u format_bytes=%d state_bytes=%u collision_tag=%u boundaries=11\n",checks,n,(unsigned)sizeof nes_budget210,collision);
 return 0;
}
'''
 (a.out/'unit.c').write_text(unit,encoding='utf8')
 run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','unit.c','nes_native165.c','nes_trace166.c','nes_budget210.c','-o','unit.exe'],'unit-build')
 summary=run([a.out/'unit.exe'],'unit')
 # Execute the actual post-format save tail, with FatFS/IRQ mocked. This
 # proves no live SD call was added to RUN and no second text buffer exists.
 menu=(a.arm/'src/nes_menu_diagnostic.c').read_text()
 tail=menu[menu.index(' if(!persist)return;'):menu.index('\nbool nes_menu_diagnostic_run(')]
 logtest=r'''
#include "nes_budget210.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef unsigned UINT;typedef int FRESULT;typedef int FIL;
enum {FR_OK,FA_CREATE_ALWAYS=2,FA_WRITE=4,OTG_FS_IRQn=1};
static bool irq=true;static unsigned opens,writes,closes,mode;
static bool NVIC_GetEnableIRQ(unsigned n){(void)n;return irq;}
static void NVIC_DisableIRQ(unsigned n){(void)n;irq=false;}
static void NVIC_EnableIRQ(unsigned n){(void)n;irq=true;}
static FRESULT f_open(FIL *f,const char *path,unsigned flags){
 (void)f;assert(!irq&&flags==(FA_CREATE_ALWAYS|FA_WRITE));
 assert(!strcmp(path,opens?"/sd2snes/nes-budget-210.txt":"/sd2snes/nes-game-last-210.txt"));
 opens++;return mode==2&&opens==2?7:FR_OK;
}
static FRESULT f_write(FIL *f,const char *text,UINT n,UINT *written){
 (void)f;assert(!irq&&n<4096);writes++;*written=n;
 if(opens==2)assert(!strncmp(text,"budget_schema=210\n",18));
 return mode==1?9:FR_OK;
}
static FRESULT f_close(FIL *f){(void)f;assert(!irq);closes++;return FR_OK;}
static void save(bool persist){
 char text[4096]="test";FIL log=0;UINT written=0;int n=4;
'''+tail+r'''
int main(void){
 nes_budget210_reset();save(false);assert(irq&&!opens&&!writes&&!closes);
 for(mode=0;mode<3;mode++){
  opens=writes=closes=0;save(true);assert(irq&&opens==2);
  assert(writes==(mode==2?1u:2u)&&closes==writes);
 }
 irq=false;mode=0;opens=writes=closes=0;save(true);assert(!irq&&opens==2);
 char text[4096];int n=nes_budget210_format(text,sizeof text);assert(n>0);
 FILE *f=fopen("budget-synthetic.txt","wb");assert(f&&fwrite(text,1,(size_t)n,f)==(size_t)n);fclose(f);
 puts("PASS BUDGET210 save_tail persist_gate=1 irq_restore=2 errors=2 same_buffer=1");return 0;
}
'''
 (a.out/'save.c').write_text(logtest,encoding='utf8')
 run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','save.c','nes_budget210.c','-o','save.exe'],'save-build')
 saved=run([a.out/'save.exe'],'save')
 from analyze_nes_budget210 import analyze
 parsed=analyze(a.out/'budget-synthetic.txt');assert not parsed['adopt_reuse'] and all(b['frames']==0 for b in parsed['bins'])
 (a.out/'budget-synthetic.json').write_text(json.dumps(parsed,indent=2)+'\n',encoding='utf8')
 r=dict(passed=True,normal=normal.strip(),unit=summary.strip(),source_pins=pins,
  changed_sources={n:sha(a.arm/'src'/n) for n in ['nes_plan191.c','nes_native_runtime165.c','nes_budget210.c','nes_budget210.h']},
  menu_source=sha(a.arm/'src/nes_menu_diagnostic.c'),save_test=saved.strip(),
  public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_budget210.py','tools/analyze_nes_budget210.py']},actual_scroll_measured=False,new_rtl=False,new_fit=False)
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(normal+summary+saved)
if __name__=='__main__':main()
