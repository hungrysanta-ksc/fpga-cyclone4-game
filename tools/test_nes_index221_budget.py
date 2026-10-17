# SPDX-License-Identifier: MIT
"""Bound221 report and distinguish encoded D1 payload from status clock bytes."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_runtime213 import ROOT,BASE,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);src=(a.arm/'src').resolve()
 def tail(s):return s[s.index(' if(!persist)return;'):s.index('\nbool nes_menu_diagnostic_run(')]
 assert tail((src/'nes_menu_diagnostic.c').read_text()).replace('221','220')==tail((BASE/'probes/nes-status220/arm01/src/nes_menu_diagnostic.c').read_text())
 code=r'''
#include "nes_budget210.h"
#include "nes_plan215.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
struct nes_plan215 nes_plan215;
int main(void){
 char text[4096];memset(&nes_budget210,255,sizeof nes_budget210);nes_budget210.open=true;
 int n=nes_budget210_format(text,sizeof text);assert(n>0&&n<4096);
 assert(strstr(text,"budget_schema=221\n")&&strstr(text,"slot_hits,planner_ticks,callback_ticks")&&strstr(text,"mapdirty,d1_payload,d0_clock\n"));
 assert(nes_budget210_format(text,32)==-1);
 nes_budget210_reset();nes_budget210_frame(0);
 nes_budget210_wire(0xd0,8,true);nes_budget210_wire(0xd1,259,true);
 nes_budget210_wire(0xd2,8,true);nes_budget210_wire(0xd3,8,true);
 nes_budget210_wire(0xd1,19,false);nes_budget210_wire(0xe8,20,true);
 uint32_t *b=nes_budget210.bins[0];
 assert(b[B210_INGRESS]==302&&b[B221_D1_PAYLOAD]==272&&b[B221_D0_CLOCK]==8);
 assert(b[B210_E8]==20&&nes_budget210.failed_transfers==1);
 assert(b[B210_REUSE_PLAN]==0&&b[B210_COMPLEX]==0);
 /* Counters are attempted wrapper bytes; the failed D1 does NOT become
  * verified geometry. Field labels and consumers must retain this limit. */
 printf("PASS BUDGET221 maximum_bytes=%d extra_bins_bytes=96 save_tail_identical220=1\n",n);
 return 0;
}
'''
 f=d/'budget.c';f.write_text(code,encoding='utf8')
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
 for name,args in [('build',[gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','-I',src,f,src/'nes_budget210.c','-o',d/'budget.exe']),('run',[d/'budget.exe'])]:
  with (d/(name+'.log')).open('wb') as log:r=subprocess.run(list(map(str,args)),stdout=log,stderr=subprocess.STDOUT,env=env,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(d/(name+'.log')).read_text(errors='replace')
 result=dict(passed=True,output=(d/'run.log').read_text(),menu_sha256=sha(src/'nes_menu_diagnostic.c'),budget_sha256=sha(src/'nes_budget210.c'),public_source_sha256=sha(Path(__file__)),save_tail_identical220_except_names=True)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result))
if __name__=='__main__':main()
