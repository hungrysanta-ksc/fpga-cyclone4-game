# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_spi_boot import ROOT,sha
from test_nes_menu098 import definition
def main():
 p=argparse.ArgumentParser()
 for n in ['arm','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--mutation',choices=['nconfig','sticky','disarm','nmi-owner'])
 a=p.parse_args();s=a.arm.resolve()/'src';o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
 def write(n,t):(o/n).write_text(t,encoding='utf-8',newline='\n')
 for n in ['nes_css108.c','nes_css108.h','nes_diag_runtime.c','nes_diag_runtime.h','nes_menu_return.h']:shutil.copy2(s/n,o/n)
 source=(s/'nes_menu_return.c').read_text(encoding='utf-8')
 write('return108.inc','static bool fault,log_allowed,io_active;\n'+definition(source,'nes_return_reset')+'\n'+definition(source,'nes_return_failed'))
 h=(s/'include/arm/ST/STM32F4/stm32f401xc.h').read_text()
 defs='\n'.join(re.findall(r'^#define (?:RCC_CR_(?:CSSON|HSEON|HSERDY|PLLRDY)|RCC_CFGR_SWS(?:_PLL)?|RCC_PLLCFGR_PLLSRC_HSE|RCC_CIR_(?:CSSC|CSSF)|RCC_APB2RSTR_SPI1RST|SPI_CR1_SPE)(?:_Pos|_Msk)?\s[^\n]*',h,re.M))
 write('config.h','''#ifndef HOST_CONFIG108
#define HOST_CONFIG108
#include <stdint.h>
#include <stdbool.h>
#include "nes_css108.h"
typedef struct {volatile uint32_t MODER,OTYPER,ODR,BSRR;} GPIO_TypeDef;
typedef struct {volatile uint32_t CR,CFGR,PLLCFGR,CIR,AHB1ENR,APB2RSTR;} RCC_TypeDef;
typedef struct {volatile uint32_t CR1,CR2;} SPI_TypeDef;
extern GPIO_TypeDef ga,gb;extern RCC_TypeDef rc;extern SPI_TypeDef sp;
#define GPIOA (&ga)
#define GPIOB (&gb)
#define RCC (&rc)
#define SPI1 (&sp)
#define OTG_FS_IRQn 67
uint32_t read108(volatile uint32_t *);
void write108(volatile uint32_t *,uint32_t,const char *);
void mask108(void);unsigned getusb108(void);void disableusb108(void);void halt108(void);
#define CSS108_READ(reg) read108(&(reg))
#define CSS108_WRITE(reg,v) write108(&(reg),(v),#reg)
#define __disable_irq() mask108()
#define NVIC_GetEnableIRQ(x) getusb108()
#define NVIC_DisableIRQ(x) disableusb108()
#define __DSB() ((void)0)
#define __DMB() ((void)0)
#define __ISB() ((void)0)
#define __NOP() halt108()
'''+defs+'\n#endif\n')
 shutil.copy2(ROOT/'tests/nes-functional/css108_host.c',o/'host.c');shutil.copy2(__file__,o/'executed-test.py')
 if a.mutation:
  f=o/('return108.inc' if a.mutation=='sticky' else 'nes_css108.c');text=f.read_text()
  old,new={
   'nconfig':('CSS108_WRITE(GPIOA->BSRR,1u<<17);','/* omitted nCONFIG */'),
   'sticky':('nes_css_fault108()||',''),
   'disarm':('CSS108_WRITE(RCC->CR,CSS108_READ(RCC->CR)&~RCC_CR_CSSON);','/* omitted disarm */'),
   'nmi-owner':('owned108||(claimed108&&css)','owned108')
  }[a.mutation];assert text.count(old)==1;write(f.name,text.replace(old,new))
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','-I.','host.c','-o','host.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 assert not r.returncode,(o/'compile.log').read_text(errors='replace')
 cases=list(range(29))+list(range(100,122))+list(range(200,212))
 if a.mutation:cases=[{'nconfig':23,'sticky':23,'disarm':18,'nmi-owner':25}[a.mutation]]
 results=[]
 for c in cases:
  with (o/f'case-{c}.log').open('wb') as f:r=subprocess.run([str(o/'host.exe'),str(c)],stdout=f,stderr=subprocess.STDOUT,timeout=10)
  log=(o/f'case-{c}.log').read_text(errors='replace')
  assert (r.returncode!=0 and 'Assertion' in log) if a.mutation else (r.returncode==0 and 'PASS108' in log),(c,log)
  results.append({'case':c,'exit':r.returncode,'sha256':sha(o/f'case-{c}.log')})
 write('result.json',json.dumps(dict(cases=results,mutation=a.mutation,physical=False,arm_execution=False,production_sources={n:sha(s/n) for n in ['nes_css108.c','nes_css108.h','nes_diag_runtime.c','nes_menu_return.c']}),indent=2)+'\n')
 print('PASS108 cases='+str(len(cases))+' mutation='+str(a.mutation))
if __name__=='__main__':main()
