# SPDX-License-Identifier: MIT
"""Actual226 RUN boundary regressions and bounded BEGIN/finish reporting."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_fast226 import ROOT,BASE,sha,once


def main():
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    src=(a.arm/'src').resolve();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
    prior=BASE/'probes/nes-scroll225/runtime01';pins={}
    for n in ['host213.c','reference203.c','reference203.h']+[f'scene{i}.wire' for i in range(11)]:
        shutil.copyfile(prior/n,d/n);pins[str((prior/n).relative_to(BASE))]=sha(prior/n)
    for f in src.iterdir():
        if f.name.startswith('nes_') and f.suffix in ['.c','.h','.inc']:shutil.copyfile(f,d/f.name)
    f=d/'host213.c';s=f.read_text()
    s=once(s,' assert(services>wire_calls&&!inside);', ''' unsigned begins226=0,finishes226=0;
 for(unsigned i=0;i<12;i++){begins226+=nes_budget210.bins[i][B226_BEGIN];finishes226+=nes_budget210.bins[i][B226_FINISH];}
 assert(begins226&&finishes226);
 printf("PHASE226 begin_ticks=%u finish_ticks=%u mocked_ticks_not_performance=1\\n",begins226,finishes226);
 assert(services>wire_calls&&!inside);''')
    s=once(s,'#include "nes_native_runtime165.h"','#include "nes_native_runtime165.h"\n#include "nes_budget210.h"')
    f.write_text(s,encoding='utf8',newline='\n')
    budget=r'''
#include "nes_budget210.h"
#include "nes_boot214.h"
#include "nes_plan215.h"
#include "nes_startup222.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
struct nes_plan215 nes_plan215;
int main(void){
 char text[4096];memset(&nes_budget210,255,sizeof nes_budget210);nes_budget210.open=true;
 memset(&nes_boot214,255,sizeof nes_boot214);memset(&nes_plan215,255,sizeof nes_plan215);
 memset(&nes_startup222,255,sizeof nes_startup222);
 int n=nes_budget210_format(text,sizeof text);assert(n>0&&n<4096);
 assert(strstr(text,"budget_schema=226\n")&&strstr(text,"d0_clock,begin_ticks,finish_ticks\n"));
 assert(nes_budget210_format(text,32)==-1);
 nes_budget210_reset();nes_budget210_frame(1000);
 nes_budget210_time(B226_BEGIN,3);nes_budget210_time(B226_FINISH,11);nes_budget210_time(B210_PLAN,25);
 nes_budget210_time(B210_FIELDS,999);nes_budget210_time(B210_FRAMES,999);
 assert(nes_budget210.bins[2][B226_BEGIN]==3&&nes_budget210.bins[2][B226_FINISH]==11);
 assert(nes_budget210.bins[2][B210_PLAN]==25&&nes_budget210.bins[2][B210_FRAMES]==0);
 nes_budget210_wire(0xd1,259,true);nes_budget210_wire(0xd0,8,true);
 assert(nes_budget210.bins[2][B221_D1_PAYLOAD]==256&&nes_budget210.bins[2][B221_D0_CLOCK]==8);
 printf("PASS BUDGET226 maximum_bytes=%d extra_static_bins=96\n",n);return 0;
}
'''
    (d/'budget.c').write_text(budget,encoding='utf8')
    gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
    env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
    files=['host213.c','reference203.c','nes_native_runtime165.c','nes_native165.c','nes_trace166.c','nes_planner211.c','nes_resident211.c','nes_plan_service200.c','nes_native_sink165.c','nes_sink_trace168.c','nes_sink_window184.c','nes_budget210.c']
    results={}
    for kind,inputs in [('runtime',files),('budget',['budget.c','nes_budget210.c'])]:
        for name,args in [('build',[gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2',*inputs,'-o',kind+'.exe']),('run',[d/(kind+'.exe')])]:
            with (d/(kind+'-'+name+'.log')).open('wb') as log:q=subprocess.run(list(map(str,args)),cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
            text=(d/(kind+'-'+name+'.log')).read_text(errors='replace');assert q.returncode==0,text[-5000:]
        results[kind]=text;print(text,flush=True)
    assert 'frames=9 ' in results['runtime'] and results['runtime'].count('PASS METADATA203 fault=')==6
    def tail(s):return s[s.index(' if(!persist)return;'):s.index('\nbool nes_menu_diagnostic_run(')]
    assert tail((src/'nes_menu_diagnostic.c').read_text()).replace('226','225')==tail((BASE/'probes/nes-scroll225/arm01/src/nes_menu_diagnostic.c').read_text())
    r=dict(passed=True,results=results,source_hashes={n:sha(d/n) for n in files},inputs=pins,save_tail_unchanged225_except_identity=True,physical=False)
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
