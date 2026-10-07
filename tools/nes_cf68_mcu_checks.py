# SPDX-License-Identifier: MIT
"""065 actual C helpers; explicit pinned private source and hardware models."""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_mcu_loader import ROOT,FW,sha,run
from nes_cf68_mcu import materialize
from nes_diag_recovery_checks import function

def main():
 p=argparse.ArgumentParser();p.add_argument('--platform',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True);p.add_argument('--mutation',choices=['menu-compare','log-release','sd-crc','fatfs-budget']);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False);materialize(a.out);shutil.copy2(__file__,a.out/'executed-driver.py')
 source=a.platform/'stm32f4xx/sdnative.c';assert sha(source)=='8df90cfb1eb2753250d08c53f82e9b218231c4ebddb941a6fe3925140f34a651','Pin final065 source before testing'
 sd=source.read_text();(a.out/'materialized-sdnative.c').write_text(sd,encoding='utf-8',newline='\n')
 (a.out/'sd-write-functions.inc').write_text(''.join(function(sd,n) for n in ['wait_busy','send_datablock']),encoding='utf-8',newline='\n')
 for n in ['nes_return_spi.inc','nes_return_timer.inc','nes_return_sd_write.inc']:shutil.copy2(FW/n,a.out/n)
 shutil.copy2(ROOT/'tests/nes-functional/mcu_loader_platform.h',a.out/'mcu_loader_platform.h')
 for n in ['config','fileops','snes']:(a.out/(n+'.h')).write_text('#include "mcu_loader_platform.h"\n')
 (a.out/'memory.h').write_text('#include "mcu_loader_platform.h"\nuint16_t sram_writeblock(void *,uint32_t,uint16_t);\nuint16_t sram_readblock(void *,uint32_t,uint16_t);\n')
 if a.mutation:
  if a.mutation=='menu-compare':name,old,new='nes_menu_return.c','||memcmp(data,verify,n)',''
  elif a.mutation=='log-release':name,old,new='nes_menu_diagnostic.c','if(nes_return_failed())return false;','if(false)return false;'
  elif a.mutation=='fatfs-budget':name,old,new='nes_menu_return.c','io_active&&!nes_diag_wait_step(&io_wait)','io_active&&false'
  else:name,old,new='sd-write-functions.inc','nes_diag_sd_error(NES_DIAG_SD_CRC);return;','return;'
  f=a.out/name;s=f.read_text();assert old in s;s=s.replace(old,new);f.write_text(s,encoding='utf-8',newline='\n')
 results={}
 kinds=['copy','wait','log','sd','fatfs','finish'] if not a.mutation else [{'menu-compare':'copy','log-release':'log','sd-crc':'sd','fatfs-budget':'fatfs'}[a.mutation]]
 for n in ['ff.h','ffconf.h','integer.h','diskio.h']:shutil.copy2(a.platform/n,a.out/n)
 ff=(a.platform/'ff.c').read_text()
 (a.out/'fatfs-cache-functions.inc').write_text(''.join(function(ff,n) for n in ['move_window','get_fat','put_fat','create_chain']),encoding='utf-8',newline='\n')
 main=(a.platform/'main.c').read_text();start=main.index('    if(!nes_menu_diagnostic_prepared(');end=main.index('    printf("ok\\n");',start)+len('    printf("ok\\n");')
 (a.out/'main-finish.inc').write_text(main[start:end],encoding='utf-8',newline='\n')

 for kind in kinds:
  shutil.copy2(ROOT/f'tests/nes-functional/menu_return_{kind}_host.c',a.out/f'{kind}-host.c')
  if kind in ['log','finish']:
   f=a.out/f'{kind}-host.c';v=f.read_text().replace('NES VERIFY 065','NES VERIFY 069');f.write_text(v,encoding='utf-8')
  if kind=='wait':
   f=a.out/f'{kind}-host.c';v=f.read_text().replace(' if(mode==2&&pin==2)', ' if(mode==3&&pin==4&&read_calls>8)bits[4]=1;\n if(mode==2&&pin==2)');v=v.replace(' printf("PASS MENU065 wait', ' setup();bits[1]=1;mode=3;assert(nes_return_spi_ready()&&read_calls>8);cases++;\n setup();bits[1]=1;assert(!nes_return_spi_ready()&&nes_return_failed()&&read_calls<1000010);cases++;\n printf("PASS MENU065 wait');f.write_text(v,encoding='utf-8')
  # Only these suites call the copy helper; its other dependencies are provided
  # by assertions that deliberately fail if an unexpected SD/SRAM call occurs.
  extra=[]
  if kind in ['wait','sd','fatfs']:
   (a.out/(kind+'-copy-stubs.c')).write_text('#include "mcu_loader_platform.h"\n#include <assert.h>\nFRESULT f_open(FIL*f,const char*p,unsigned m){(void)f;(void)p;(void)m;assert(0);return 1;}\nFRESULT f_read(FIL*f,void*p,UINT n,UINT*g){(void)f;(void)p;(void)n;(void)g;assert(0);return 1;}\nFRESULT f_close(FIL*f){(void)f;assert(0);return 1;}\nFRESULT f_lseek(FIL*f,uint32_t a){(void)f;(void)a;assert(0);return 1;}\nuint16_t sram_writeblock(void*p,uint32_t a,uint16_t n){(void)p;(void)a;(void)n;assert(0);return 0;}\nuint16_t sram_readblock(void*p,uint32_t a,uint16_t n){(void)p;(void)a;(void)n;assert(0);return 0;}\n')
   extra=[kind+'-copy-stubs.c']
  run([a.gcc,'-std=c11','-D__USE_MINGW_ANSI_STDIO=1','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-O2','nes_diag_runtime.c','nes_menu_return.c',*extra,kind+'-host.c','-o',kind+'.exe'],a.out,kind+'-compile')
  with (a.out/(kind+'.log')).open('wb') as f:cp=subprocess.run([str(a.out.resolve()/(kind+'.exe'))],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=30)
  log=(a.out/(kind+'.log')).read_text(errors='replace')
  if a.mutation:
   case={'menu-compare':'COPY fault=6','log-release':'LOG fault=4 irq=0','sd-crc':'SD_WRITE fault=3','fatfs-budget':'FATFS cached budget'}[a.mutation]
   target={'menu-compare':'!nes_return_copy_menu("menu",0,0)&&nes_return_failed()','log-release':'ready==!blocked','sd-crc':'nes_return_sd_write(0,data,7,2)==RES_ERROR','fatfs-budget':'n<10001&&!reads&&nes_return_failed()'}[a.mutation]
   assert cp.returncode!=0 and 'Assertion' in log and case in log and target in log,log
  else:assert cp.returncode==0 and 'PASS MENU065' in log,log
  results[kind]=dict(exit_code=cp.returncode,last_line=log.strip().splitlines()[-1])
 (a.out/'result.json').write_text(json.dumps(dict(candidate='NES-CF68-MCU-069',actual_stm32_execution=False,mutation=a.mutation,results=results,files={f.name:sha(f) for f in a.out.iterdir() if f.is_file()}),indent=2)+'\n')
 print(json.dumps(results))
if __name__=='__main__':main()
