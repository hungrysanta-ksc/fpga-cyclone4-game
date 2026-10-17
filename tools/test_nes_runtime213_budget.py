# SPDX-License-Identifier: MIT
"""Actual213 counter formatter and unchanged safe post-STOP save tail."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_runtime213 import ROOT,BASE,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False);src=(a.arm/'src').resolve()
 current=(src/'nes_menu_diagnostic.c').read_text();old=(BASE/'probes/nes-budget210/arm03/src/nes_menu_diagnostic.c').read_text()
 def tail(s):return s[s.index(' if(!persist)return;'):s.index('\nbool nes_menu_diagnostic_run(')]
 assert tail(current).replace('213','210')==tail(old) # verified210 gate/IRQ/error path unchanged
 code=r'''
#include "nes_budget210.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void){
 char text[4096];memset(&nes_budget210,255,sizeof nes_budget210);nes_budget210.open=true;
 int n=nes_budget210_format(text,sizeof text);assert(n>0&&n<4096);
 assert(strstr(text,"budget_schema=213\n")&&strstr(text,"ACTUAL_BANK_RESIDENT_SLOTS_211")&&strstr(text,"slot_hits,reserved0,reserved1"));
 assert(nes_budget210_format(text,32)==-1);
 nes_budget210_reset();nes_budget210_frame(0);
 struct nes_plan191 q={0};q.kind=0;nes_budget210_plan(&q);q.kind=1;nes_budget210_plan(&q);
 assert(nes_budget210.bins[0][B210_PLANS]==2&&nes_budget210.bins[0][B210_OUTPUT]==48&&!nes_budget210.cache);
 printf("PASS BUDGET213 format_max=%d same_save_tail=1 no_model_cache=1\n",n);return 0;
}
'''
 f=a.out/'budget.c';f.write_text(code,encoding='utf8')
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
 for label,args in [('build',[gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','-I',src,f,src/'nes_budget210.c','-o',a.out/'budget.exe']),('run',[a.out/'budget.exe'])]:
  with (a.out/(label+'.log')).open('wb') as log:r=subprocess.run(list(map(str,args)),stdout=log,stderr=subprocess.STDOUT,env=env,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(a.out/(label+'.log')).read_text(errors='replace')
 result=dict(passed=True,output=(a.out/'run.log').read_text(),menu_sha256=sha(src/'nes_menu_diagnostic.c'),budget_sha256=sha(src/'nes_budget210.c'),save_tail_identical210_except_names=True)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result))
if __name__=='__main__':main()
