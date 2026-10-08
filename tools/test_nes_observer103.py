# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_spi_boot import ROOT,sha
from nes_menu098 import once
from test_nes_menu098 import definition
from test_nes_quiesce102 import helper

def formatter(s,o):
 text=(s/'printf.c').read_text()
 for n in ['printf','vprintf','snprintf','vsnprintf','puts','putchar']:
  text=re.sub(r'\bint '+n+r'\(', 'int diag_'+n+'(',text)
 (o/'printf103.c').write_text(text,encoding='utf-8',newline='\n')
 (o/'config.h').write_text('#include <stdint.h>\n',encoding='utf-8')
 (o/'uart.h').write_text('void uart_putc(char);\nvoid uart_puts(const char *);\n',encoding='utf-8')

def main():
 p=argparse.ArgumentParser()
 for n in ['arm','evidence102','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--mutation',choices=['baseline','observer','uart','flush','scope','order'])
 a=p.parse_args();s=a.arm.resolve()/'src';e=a.evidence102.resolve();o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/quiesce102-verification.json').read_bytes())['manifest_sha256']
 def write(n,t):(o/n).write_text(t,encoding='utf-8',newline='\n')
 shutil.copy2(__file__,o/'executed-test103.py');shutil.copy2(ROOT/'tests/nes-functional/observer103_model.c',o/'model.c')
 for n in ['nes_diag_runtime.c','nes_diag_runtime.h']:shutil.copy2(s/n,o/n)
 for n in ['nes_diag_platform.c','stm32f4xx/uart.c','nes_menu_return.c','stm32f4xx/sdnative.c','printf.c','snes.c']:
  shutil.copy2(s/n,o/('production-'+n.replace('/','-')))
 shutil.copy2(e/'pins01/registers102.h',o/'registers.h')
 platform=(s/'nes_diag_platform.c').read_text();uart=(s/'stm32f4xx/uart.c').read_text()
 if a.mutation=='baseline':platform=(e/'arm01/src/nes_diag_platform.c').read_text();uart=(e/'arm01/src/stm32f4xx/uart.c').read_text()
 observe=definition(platform,'nes_diag_observe')
 if a.mutation=='observer':observe=once(observe,'  nes_diag_spi_quiesce102();','  /* omitted isolation */')
 if a.mutation=='scope':observe=once(observe,'active&&nes_return_failed()','active&&r->error')
 if a.mutation=='order':observe=once(observe,'  nes_diag_spi_quiesce102();','  nes_diag_led_tick();nes_diag_spi_quiesce102();')
 for n in ['uart_putc','uart_flush']:
  f=definition(uart,n)
  if (a.mutation=='uart' and n=='uart_putc') or (a.mutation=='flush' and n=='uart_flush'):
   f=once(f,'  if(nes_diag_active()&&nes_return_failed()){nes_diag_uart_dropped++;return;}','  /* omitted suppression */')
  write(n+'.inc',f)
 write('uart.inc','#include "uart_putc.inc"\n#include "uart_flush.inc"\n'+definition(uart,'uart_puts'))
 declarations=platform[platform.index('static volatile unsigned led_phase'):platform.index('uint32_t nes_diag_ticks')]
 write('observer.inc',declarations+definition(platform,'nes_diag_ticks')+definition(platform,'nes_diag_led_tick')+observe)
 write('reset.inc',definition((s/'snes.c').read_text(),'snes_reset'));write('quiesce.inc',helper(platform));write('blocked.inc',definition(platform,'nes_diag_blocked'))
 shared=definition((s/'nes_menu_return.c').read_text(),'nes_return_fail')+definition((s/'nes_menu_return.c').read_text(),'nes_return_failed')+definition((s/'stm32f4xx/sdnative.c').read_text(),'nes_diag_sd_error')
 shared=re.sub(r'\bfault\b','shared',shared);shared=re.sub(r'\bnes_diag_sd_fault\b','sd_fault',shared)
 write('shared.inc',shared);formatter(s,o)
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-implicit-fallthrough','-fno-builtin','-I.','model.c','nes_diag_runtime.c','printf103.c','-o','test.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 assert not r.returncode,(o/'compile.log').read_text()
 cases=[0 if a.mutation=='scope' else 4] if a.mutation else range(17);results=[]
 for case in cases:
  log=o/f'case-{case}.log'
  with log.open('wb') as f:r=subprocess.run([str(o/'test.exe'),str(case)],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=30)
  text=log.read_text(errors='replace')
  if a.mutation:assert r.returncode and 'Assertion' in text,text
  else:assert not r.returncode and 'PASS103' in text,text
  results.append(dict(case=case,exit=r.returncode,log_sha256=sha(log),last=text.strip().splitlines()[-1]))
 write('result.json',json.dumps(dict(cases=results,mutation=a.mutation,physical=False,installable=False),indent=2)+'\n')
 print('PASS103 observer/formatter/UART cases='+str(len(results)))
if __name__=='__main__':main()
