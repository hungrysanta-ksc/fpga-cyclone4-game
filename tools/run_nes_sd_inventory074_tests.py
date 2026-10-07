# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil,subprocess,hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 out=a.out.resolve();src=a.source.resolve();tests=ROOT/'tests/nes-functional'
 def write(n,s):(out/n).write_text(s,encoding='utf-8',newline='\n')
 def run(name,args,marker):
  with (out/(name+'.log')).open('wb') as log:r=subprocess.run([str(x) for x in args],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=60)
  text=(out/(name+'.log')).read_text(errors='replace')
  assert r.returncode==0 and marker in text,(name,text)
 for n in ['sd_inventory_mock_hw.h','sd_inventory_ff_mock.h']:shutil.copy2(tests/n,out/n)
 write('config.h','#include "sd_inventory_mock_hw.h"\n')
 write('snes.h','#include "sd_inventory_mock_hw.h"\n')
 write('diskio.h','/* no disk_status */\n')
 write('ff.h','#include "sd_inventory_ff_mock.h"\n#define FR_NO_FILE 4\n#define FR_NO_PATH 5\n#define fptr pos\nFRESULT f_lseek(FIL *,uint32_t);\n')
 write('timer.h','#include <stdint.h>\nuint32_t getticks(void);\n')
 write('led.h','void rdyled(int);void readled(int);void writeled(int);void led_std(void);void led_pwm(void);\n')
 # Copy exact executed source out of the full source tree to give mock headers
 # precedence over production ff.h (quoted includes search source dir first).
 for n in ['nes_sd_inventory.c','nes_sd_inventory_log.c','nes_sd_inventory_platform.c','nes_diag_runtime.c','nes_diag_runtime.h','nes_menu_return.h','nes_sd_inventory.h','nes_sd_inventory_log073.h','nes_sd_fault074.h','nes_diag_platform.c']:shutil.copy2(src/n,out/n)
 jobs=[('collector','sd_inventory073_host.c',['nes_sd_inventory.c'],'checks=52'),('writer','sd_inventory_log073_host.c',['nes_sd_inventory_log.c'],'checks=23'),('platform','sd_inventory_platform073_host.c',['nes_sd_inventory_platform.c','nes_diag_runtime.c'],'sessions=6'),('led','sd_fault074_host.c',['nes_diag_platform.c','nes_diag_runtime.c'],'LED cases=162')]
 for name,test,units,marker in jobs:
  text=(tests/test).read_text().replace('HW004','HW005').replace('SDINFO073','SDINFO074').replace('NES-SD-INSPECTION-073','NES-SD-INSPECTION-074')
  if name=='writer':
   text=text.replace('static bool window;','static unsigned checkpoint;\nvoid sdinv_fault_stage(unsigned n){checkpoint=n;}\nstatic bool window;')
   for needle,stage in [('opens++;',2),('writes++;',3),('syncs++;',4),('reads++;',7)]:
    # f_open has separate write and read stages.
    assertion='assert(checkpoint==2||checkpoint==6);' if stage==2 else 'assert(checkpoint=='+str(stage)+');'
    text=text.replace(needle,assertion+needle)
   text=text.replace('closes++;','assert(checkpoint==5||checkpoint==8);closes++;')
  if name=='platform':text+='\nvoid sdinv_fault_stage(unsigned n){assert(n==1||n==9); }\n'
  write(name+'.c',text)
  run(name+'-compile',[a.gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-clobbered','-DSDINFO_HOST_TEST','-I.',name+'.c',*units,'-o',name+'.exe'],'')
  run(name,[out/(name+'.exe'),out/'SYNTHETIC-NOT-HARDWARE.TXT'] if name=='collector' else [out/(name+'.exe')],marker)
 # The checker import and sample framing are the same parser with074 identity.
 for n in ['check_nes_sd_inventory073.py']:
  write(n,(ROOT/'tools'/n).read_text().replace('073','074'))
 text=(tests/'sd_inventory_report073_test.py').read_text().replace("Path(__file__).resolve().parents[2]/'tools'","Path(__file__).resolve().parent").replace('SDINFO073','SDINFO074')
 write('report_test.py',text)
 run('report',[sys.executable,'-B',out/'report_test.py',out/'SYNTHETIC-NOT-HARDWARE.TXT'],'checks=29')
 result=dict(candidate='SDINFO074',collector=52,writer=23,platform=6,led=162,report=29,hardware=False,sources={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ['nes_sd_inventory.c','nes_sd_inventory_log.c','nes_sd_inventory_platform.c','nes_diag_platform.c']})
 write('result.json',json.dumps(result,indent=2)+'\n');print('PASS074 collector52 writer23 platform6 LED162 report29')
if __name__=='__main__':main()
