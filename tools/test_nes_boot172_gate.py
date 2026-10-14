# SPDX-License-Identifier: MIT
"""Execute the deployed pre-BEGIN gate with delayed/faulted boot and tick wrap."""
from pathlib import Path
import argparse,json,subprocess,os
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['out','gcc']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 source=(ROOT/'src/nes/firmware/nes_boot172.inc').read_text()
 harness=r'''
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <assert.h>
#include <stdio.h>
struct nes_rom_spi_io {int dummy;};
enum {NES_RUNTIME165_SERVICE=2};
static struct {unsigned result;} native_runtime165;
static struct {unsigned screen_stage,first_error;} nes_run136;
static unsigned calls,mode;
static uint32_t ticks;
static uint32_t getticks(void){return ticks;}
static bool native_service165(void *p){(void)p;if(mode==4){nes_run136.first_error=1;return false;}return true;}
static bool screen146(const struct nes_rom_spi_io *p){
 (void)p;calls++;
 if(mode!=6)ticks++;
 if(mode==5)return false;
 nes_run136.screen_stage=mode==0?3:mode==1?(calls>=10?3:2):mode==3?0xe1:mode==7?1:mode==8?2:0;
 return true;
}
'''+source+r'''
int main(void){
 struct nes_rom_spi_io io={0};
 for(mode=0;mode<9;mode++){
  calls=0;ticks=mode==2?UINT32_MAX-100:0;nes_run136.first_error=0;nes_run136.screen_stage=0;native_runtime165.result=0;
  bool ok=native_boot172(&io);
  assert(ok==(mode<2));
  if(ok){assert(native_runtime165.result==0&&nes_run136.first_error==0);assert(calls==(mode==0?1:10));}
  else {assert(native_runtime165.result==2);assert(nes_run136.first_error==(mode==4?1:6));
   assert(calls==(mode==3||mode==5?1:mode==4?0:mode==6?65536:500));}
 }
 puts("PASS 9 gate cases: ready/delayed/wrap/mismatch/service/status/stalled-clock/ROM-stage/WRAM-stage");
}
'''
 (a.out/'gate.c').write_text(harness,encoding='utf-8')
 env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','')
 with (a.out/'build.log').open('wb') as f:
  q=subprocess.run([str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror',str(a.out/'gate.c'),'-o',str(a.out/'gate.exe')],env=env,stdout=f,stderr=subprocess.STDOUT)
 assert q.returncode==0,(a.out/'build.log').read_text()
 q=subprocess.run([str((a.out/'gate.exe').resolve())],env=env,capture_output=True);(a.out/'test.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
 result=dict(passed=True,cases=9,gate_sha256=sha(ROOT/'src/nes/firmware/nes_boot172.inc'),scope='Actual C gate with mocked clocks/status; no physical boot claim')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(q.stdout.decode())
if __name__=='__main__':main()
