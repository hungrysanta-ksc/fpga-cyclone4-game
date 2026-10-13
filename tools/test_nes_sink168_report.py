# SPDX-License-Identifier: MIT
"""Execute the actual generated report formatter with type-width maxima."""
from pathlib import Path
import argparse,json,subprocess,os
from nes_game147 import sha
def main():
 p=argparse.ArgumentParser()
 for n in ['arm','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);src=a.arm/'src'
 s=(src/'nes_menu_diagnostic.c').read_text();s=s[s.index('static int pad165_format'):s.index(' printf("%s",text);')]
 s=s.replace('static void save_report(const char *menu_state,bool persist)','static int save_report(const char *menu_state)').replace('FIL log;UINT written=0;','').replace('return;','return -1;')+' return n;\n}\n'
 pre='''#include <stdio.h>
#include <string.h>
#include <assert.h>
#include "nes_menu_probe.h"
#include "nes_run136.h"
#include "nes_native_runtime165.h"
#include "nes_trace166.h"
#include "nes_sink_trace168.h"
static struct nes_menu_probe_report report;
struct nes_run136_report nes_run136;
struct nes_native_runtime165 native_runtime165;
struct nes_trace166 nes_trace166;
static bool safe_to_reload=true;
static unsigned geometry=~0u;
'''
 main='''
int main(void){
 memset(&report,255,sizeof report);report.board_seen=true;report.sd.verified=true;
 report.sd.load.chr_32k=true;report.sd.load.end_accepted=true;report.sd.load.stop_ok=true;report.sd.load.base_restored=true;report.sd.load.recovery_attempted=true;report.sd.verify.stop_ok=true;
 memset(&nes_run136,255,sizeof nes_run136);nes_run136.start_sent=true;nes_run136.stop_ok=true;nes_run136.passed=true;nes_run136.pad_count=16;nes_run136.history_count=16;
 memset(&native_runtime165,255,sizeof native_runtime165);memset(&nes_trace166,255,sizeof nes_trace166);
 memset(&nes_sink_trace168,255,sizeof nes_sink_trace168);nes_sink_trace168.valid=1;nes_sink_trace168.ack_valid=1;nes_sink_trace168.mismatch=63;
 int n=save_report("RETURN_READY_RESET_RELEASED");assert(n>0&&n<4096);
 printf("PASS actual_report_max_width_bytes=%d capacity=4096 full_pad16_history16=1 trace169=1\\n",n);return 0;
}
'''
 f=a.out/'report.c';f.write_text(pre+s+main,encoding='utf8');env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','')
 for args,label in [([str(a.gcc),'-std=c11','-Wall','-Wextra','-Werror','-O2','-I',str(src),str(f),str(src/'nes_sink_trace168.c'),'-o',str(a.out/'report.exe')],'build'),([str(a.out/'report.exe')],'run')]:
  with (a.out/(label+'.log')).open('wb') as out:q=subprocess.run(args,stdout=out,stderr=subprocess.STDOUT,env=env,timeout=60)
  assert q.returncode==0,(a.out/(label+'.log')).read_text(errors='replace')
 result=dict(passed=True,output=(a.out/'run.log').read_text(),generated_sha256=sha(f),source_sha256=sha(src/'nes_menu_diagnostic.c'),scope='Actual formatter extracted through post-STOP text completion; uint32/uint16/uint8 maxima,16 all-buttons entries and16 history entries, longest menu label. No SD IO.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
