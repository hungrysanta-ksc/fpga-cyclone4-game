# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_spi_boot import ROOT,sha
from nes_menu098 import once

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence104','evidence108','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--geometry96',action='store_true')
 p.add_argument('--cases',default='normal')
 p.add_argument('--mutation',choices=['begin','end','nconfig','sticky'])
 a=p.parse_args();e=a.evidence104.resolve();e108=a.evidence108.resolve();o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
 inputs={}
 for archive,meta in [(e,'timer104'),(e108,'css108')]:
  assert sha(archive/'manifest.json')==json.loads((ROOT/f'analysis/{meta}-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];p108=json.loads((e108/'manifest.json').read_bytes())['files']
 source=e/('fat32-96-02' if a.geometry96 else 'main02');s=e108/'arm02/src'
 def write(n,t):(o/n).write_text(t,encoding='utf-8',newline='\n')
 def edit(n,old,new):write(n,once((o/n).read_text(encoding='utf-8'),old,new))
 for f in source.rglob('*'):
  if f.is_file() and f.suffix in ['.c','.h','.inc','.packed','.raw','.bin','.nes']:
   key=f.relative_to(e).as_posix();assert sha(f)==pins[key];inputs['104/'+key]=sha(f)
   dst=o/f.relative_to(source);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
 # Same complete C files as the final108 ARM. Existing wrappers only redirect printf.
 names=['nes_css108.c','nes_css108.h','nes_diag_runtime.c','nes_menu_return.c','nes_h1_stm32.c']
 for n in names:
  key='arm02/src/'+n;assert sha(s/n)==p108[key];inputs['108/'+key]=sha(s/n);shutil.copy2(s/n,o/n)
 for n in ['css109_model.inc','css109_checks.inc']:shutil.copy2(ROOT/'tests/nes-functional'/n,o/n)
 cmsis=s/'include/arm/ST/STM32F4/stm32f401xc.h';assert sha(cmsis)==p108[cmsis.relative_to(e108).as_posix()]
 defs='\n'.join(re.findall(r'^#define (?:RCC_CR_(?:CSSON|HSEON|HSERDY|PLLRDY)|RCC_CFGR_SWS(?:_PLL)?|RCC_PLLCFGR_PLLSRC_HSE|RCC_CIR_(?:CSSC|CSSF))(?:_Pos|_Msk)?\s[^\n]*',cmsis.read_text(),re.M))
 write('css109_registers.h','#ifndef CSS109_REGISTERS\n#define CSS109_REGISTERS\n#include "mcu_loader_platform.h"\n#include "constants102.h"\n'+defs+'''
typedef struct {uint32_t CR,CFGR,PLLCFGR,CIR,AHB1ENR,APB2RSTR;} RCC109;
extern RCC109 rcc109;
#define RCC (&rcc109)
void event109(unsigned);
uint32_t read109(uint32_t *);
void write109(uint32_t *,uint32_t);
void mask109(void);void halt109(void);
#define CSS108_READ(r) read109(&(r))
#define CSS108_WRITE(r,v) write109(&(r),(v))
#define __disable_irq() mask109()
#define __DSB() ((void)0)
#define __ISB() ((void)0)
#define __DMB() ((void)0)
#define __NOP() halt109()
#endif
''')
 # Keep CSS shim local to its translation unit, avoiding the timer/UART macro seams.
 write('linked109-css.c','#include "css109_registers.h"\n#include "nes_css108.c"\n')
 edit('mcu_loader_platform.h','#define FPGA_MCU_RDY_REG GPIOA','#define FPGA_MCU_RDY_REG GPIOB')
 edit('mcu_loader_platform.h','#define FPGA_MCU_RDY_BIT 5','#define FPGA_MCU_RDY_BIT 8')
 edit('mcu_loader_platform.h','#define FPGA_PROGBBIT 6','#define FPGA_PROGBBIT 1')
 # Verify these physical definitions against the pinned final ARM configuration.
 autoconf=s/'obj-nes-100/autoconf.h';assert sha(autoconf)==p108[autoconf.relative_to(e108).as_posix()]
 ac=autoconf.read_text()
 for macro,value in [('FPGA_PROGBREG','GPIOA'),('FPGA_PROGBBIT','1'),('FPGA_MCU_RDY_REG','GPIOB'),('FPGA_MCU_RDY_BIT','8')]:
  assert re.search(r'^#define\s+'+macro+r'\s+\(?'+value+r'\)?\s*$',ac,re.M),macro
 edit('platform.c','mock_b.IDR=val?16:0;','mock_b.IDR=(mock_b.IDR&~16u)|(val?16u:0);')
 edit('platform.c','else mock_a.IDR=0;','else mock_b.IDR&=~256u;')
 edit('platform.c','void mock_pin(MockGPIO *port,unsigned pin,bool high) {','void mock_pin(MockGPIO *port,unsigned pin,bool high) {\n event109(4);')
 edit('platform.c','void NVIC_EnableIRQ(int n){','void NVIC_EnableIRQ(int n){event109(6);')
 edit('platform.c','#include "mcu_loader_platform.h"','#include "mcu_loader_platform.h"\nvoid event109(unsigned);')
 edit('host098-prefix.inc','if(measured096)assert(!irq&&nes_diag_active());','if(measured096)assert(!irq&&nes_diag_active());event109(1);')
 edit('host098-prefix.inc','bit==5','bit==8')
 edit('host098-prefix.inc','mock_a.IDR|=32;value=mock_a.IDR;','mock_b.IDR|=256;value=mock_b.IDR;')
 edit('host098-prefix.inc','mock_a.IDR=(mock_a.IDR&~64u)|((n||scenario096==1001)?64u:0);','mock_a.ODR=(mock_a.ODR&~2u)|(n?2u:0);mock_a.IDR=(mock_a.IDR&~2u)|((n||scenario096==1001)?2u:0);')
 edit('host098-prefix.inc','unsigned at=config_bytes096;','event109(configs==1?2:3);unsigned at=config_bytes096;')
 edit('host098-prefix.inc','mock_a.IDR|=32;','mock_b.IDR|=256;')
 edit('host098-prefix.inc','mock_a.IDR&=~32u;','mock_b.IDR&=~256u;')
 edit('lower100_model.h','if(!lower_active100)return mock_a.IDR;','if(!lower_active100)return mock_b.IDR;')
 edit('lower100_model.h','stuck100==4?0:32;','stuck100==4?0:256;')
 edit('lower100_model.h','snapshot100();tx100++;','event109(5);snapshot100();tx100++;')
 edit('quiesce-main102.inc','static struct {uint32_t APB2RSTR;} rcc102;\n#define RCC (&rcc102)','#define rcc102 rcc109\n#define RCC (&rcc109)')
 host=(o/'host104.c').read_text();host=once(host,'#include "constants102.h"','#include "css109_registers.h"\n#undef __DSB\n#undef __NOP\n#include "nes_css108.h"')
 host=once(host,'#include "peripherals104_cases.inc"','#include "peripherals104_cases.inc"\n#include "css109_model.inc"\n#include "css109_checks.inc"')
 host=once(host,'initialize(NONE,1);mock_a.IDR=32;setup_rtc099(baseline098);','initialize(NONE,1);mock_b.IDR=256;setup_rtc099(baseline098);\n init109();')
 host=once(host,'assert(nes_menu_diagnostic_run','if(setjmp(nmi_env109)){check_nmi109();return 0;}\n if(css_case109>=20&&css_case109<=22){check_reject109();return 0;}\n assert(nes_menu_diagnostic_run')
 host=once(host,'if(baseline098){\n  assert(terminal102','if(css_case109)assert(!"requested CSS fault not injected");\n if(baseline098){\n  assert(terminal102')
 host=once(host,'if(first_error096)assert','assert(!nes_css_fault108());if(ok)assert(!(RCC->CR&RCC_CR_CSSON));else assert(RCC->CR&RCC_CR_CSSON);\n if(first_error096)assert')
 host=host.replace('PASS104','PASS109');write('host109.c',host)
 if a.mutation:
  n,old,new={'begin':('nes_h1_stm32.c','if(!nes_css_begin108())','if(false)'), 'end':('nes_diag_runtime.c','if(!nes_css_end108())','if(false)'), 'nconfig':('nes_css108.c','CSS108_WRITE(GPIOA->BSRR,1u<<17);','/* removed nCONFIG */'), 'sticky':('nes_menu_return.c','nes_css_fault108()||','')}[a.mutation];edit(n,old,new)
 sources=['card.c','host109.c','printf103.c','linked109-css.c']+['linked103-'+n.replace('/','-') for n in ['ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c']]
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-fno-builtin','-ffunction-sections','-fdata-sections','-I.', '-DGBC_SAVE_G12','-DGBC_DUMP_G12',*sources,'-Wl,--gc-sections','-o','host.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 assert not r.returncode,(o/'compile.log').read_text(errors='replace')[-6000:]
 cases=[x['case'] for x in json.loads((source/'result.json').read_bytes())['cases']] if a.cases=='normal' else [[0,200+int(x)] for x in a.cases.split(',')]
 results=[]
 for i,c in enumerate(cases):
  log=o/f'case-{i}.log'
  with log.open('wb') as f:r=subprocess.run([str(o/'host.exe'),*map(str,c),*[str(o/n) for n in ['fixture.nes','diag.packed','diag.raw','base.packed','base.raw','menu.bin']]],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  text=log.read_text(errors='replace')
  assert (r.returncode and 'Assertion' in text) if a.mutation else (not r.returncode and 'PASS109' in text),(c,r.returncode,text[-2500:])
  results.append(dict(case=c,exit=r.returncode,log_sha256=sha(log),last=text.strip().splitlines()[-1]))
 shutil.copy2(__file__,o/'executed-test109.py')
 write('result.json',json.dumps(dict(cases=results,inputs=inputs,production_sources={n:sha(s/n) for n in names},mutation=a.mutation,geometry96=a.geometry96,physical=False,installable=False),indent=2)+'\n')
 print('PASS109 cases='+str(len(cases))+' mutation='+str(a.mutation))
if __name__=='__main__':main()
