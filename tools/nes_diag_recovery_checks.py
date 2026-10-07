# SPDX-License-Identifier: MIT
"""Execute production064 helpers; pinned private platform required for SD.
GPIO/FatFS/card are models. This is not a hardware qualification.
"""
from pathlib import Path
import argparse,shutil,json,subprocess,re
from nes_mcu_loader import ROOT,FW,sha,run
from nes_diag_recovery import sd_source,uart_source,PINNED

def function(s,name):
 at=re.search(r'\b'+name+r'\s*\(',s).start();start=s.rfind('\n',0,at)+1;left=s.index('{',at);depth=1;right=left+1
 while depth:
  depth+=(s[right]=='{')-(s[right]=='}');right+=1
 return s[start:right]+'\n'

def main():
 p=argparse.ArgumentParser();p.add_argument('--platform',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True);p.add_argument('--mutation',choices=['sd-success','fpga-done']);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False)
 for n in ['stm32f4xx/sdnative.c','stm32f4xx/uart.c']:assert sha(a.platform/n)==PINNED[n],n
 shutil.copy2(__file__,a.out/'executed-driver.py')
 for n in ['nes_diag_runtime.c','nes_diag_runtime.h','nes_diag_fpga.inc','nes_diag_sd.inc']:shutil.copy2(FW/n,a.out/n)
 raw=(a.platform/'stm32f4xx/sdnative.c').read_text();s=sd_source(raw)
 (a.out/'materialized-sdnative.c').write_text(s,encoding='utf-8',newline='\n')
 (a.out/'sd-command-functions.inc').write_text(''.join(function(s,n) for n in ['get_and_check_datacrc','wait_busy','send_command_fast']),encoding='utf-8',newline='\n')
 (a.out/'sd-read-function.inc').write_text(function(s,'sdn_read'),encoding='utf-8',newline='\n')
 uart=uart_source((a.platform/'stm32f4xx/uart.c').read_text())
 (a.out/'uart-functions.inc').write_text(function(uart,'uart_putc')+function(uart,'uart_flush'),encoding='utf-8',newline='\n')
 shutil.copy2(ROOT/'tests/nes-functional/diag_recovery_uart_host.c',a.out/'uart-host.c')
 hashes={'ff.c':'adcd3facbc7c33399b68baaf976aceb39c1b2bb8402bf034aff55bbe86748bb4','ff.h':'d4fbf751105313be95f603a0b120f5d553cb200fc084cfabc2f20575b0a3b90f',
  'ffconf.h':'bf3f5e6781d50b390f4130d48edf984c6e4b93f4cc582adce2a843be0a9e8762','integer.h':'83b1b8350e5e9d256eaf5817eaf2bb342df488a1fa937efc204389e484fe1dc8',
  'diskio.h':'5aa9ba742ca6dbab5f4487796a66d6982f47c6ce826f36bd4bb90e68f9d4d4ef'}
 for n,h in hashes.items():assert sha(a.platform/n)==h,n
 for n in ['ff.h','ffconf.h','integer.h','diskio.h']:shutil.copy2(a.platform/n,a.out/n)
 ff=(a.platform/'ff.c').read_text()
 # Declarations in comments/callers precede the definitions; take each
 # definition by its return type, then retain its original function bytes.
 definitions=''
 for n,ret in [('validate','FRESULT'),('clust2sect','DWORD'),('f_read','FRESULT')]:
  start=re.search(r'^'+ret+r' '+n+r'\s*\(',ff,re.M).start();definitions+=function(ff[start:],n)
 (a.out/'fatfs-read-functions.inc').write_text(definitions,encoding='utf-8',newline='\n')
 shutil.copy2(ROOT/'tests/nes-functional/diag_recovery_fatfs_host.c',a.out/'fatfs-host.c')
 shutil.copy2(FW/'nes_diag_platform.c',a.out/'nes_diag_platform.c')
 shutil.copy2(ROOT/'tests/nes-functional/diag_recovery_led_host.c',a.out/'led-host.c')
 header='''#include <stdint.h>
#define OTG_FS_IRQn 67
#define __NOP() ((void)0)
unsigned getticks(void);
void rdyled(unsigned);void readled(unsigned);void writeled(unsigned);
void led_pwm(void);void led_std(void);void NVIC_DisableIRQ(unsigned);void snes_reset(unsigned);
'''
 (a.out/'config.h').write_text(header)
 for n in ['timer','led','snes']:(a.out/(n+'.h')).write_text('')
 for kind in ['fpga','sd']:shutil.copy2(ROOT/f'tests/nes-functional/diag_recovery_{kind}_host.c',a.out/f'{kind}-host.c')
 if a.mutation:
  name='nes_diag_sd.inc' if a.mutation=='sd-success' else 'nes_diag_fpga.inc'
  f=a.out/name;t=f.read_text();old='disk_state=DISK_ERROR;return RES_ERROR;' if a.mutation=='sd-success' else 'ok=nes_diag_pin_wait(2,true,NES_DIAG_FPGA_DONE);'
  assert t.count(old)==1;t=t.replace(old,'disk_state=DISK_ERROR;return RES_OK;' if a.mutation=='sd-success' else 'ok=true;');f.write_text(t)
 results={}
 for kind in ['fpga','sd','led','uart','fatfs']:
  if a.mutation and kind!=('sd' if a.mutation=='sd-success' else 'fpga'):continue
  extra=['nes_diag_platform.c'] if kind=='led' else []
  run([a.gcc,'-std=c11','-Wall','-Wextra','-Werror','-Wno-implicit-fallthrough','-O2','nes_diag_runtime.c',*extra,kind+'-host.c','-o',kind+'.exe'],a.out,kind+'-compile')
  with (a.out/(kind+'.log')).open('wb') as log:cp=subprocess.run([str(a.out.resolve()/(kind+'.exe'))],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=30)
  output=(a.out/(kind+'.log')).read_text(errors='replace')
  if a.mutation:
   target='sdn_read(0,data,1,2)==RES_ERROR&&commands==1&&nes_diag_sd_fault&&!legacy_reads' if a.mutation=='sd-success' else '!nes_diag_fpga_pgm((const uint8_t *)"fixture")'
   case='SD stub=1' if a.mutation=='sd-success' else 'FPGA fault=7'
   assert cp.returncode!=0 and 'Assertion' in output and target in output and case in output,output
  else:assert cp.returncode==0 and 'PASS RECOVERY064' in output,output
  results[kind]=dict(exit_code=cp.returncode,marker=output.strip().splitlines()[-1])
 result=dict(candidate='NES-DIAG-RECOVERY-064',actual_stm32_execution=False,mutation=a.mutation,results=results,
  platform_sd_sha256=sha(a.platform/'stm32f4xx/sdnative.c'),files={f.name:sha(f) for f in a.out.iterdir() if f.is_file()})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(results))
if __name__=='__main__':main()
