# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_spi_boot import ROOT,sha
from test_nes_menu098 import definition
from nes_menu098 import once

def helper(src):
 text=definition(src,'nes_diag_spi_quiesce102');lines=[];index=0
 for line in text.splitlines():
  lines.append(line)
  if line.strip().endswith(';'):
   index+=1;lines.append(f' step102({index});')
 return '\n'.join(lines)+'\n'

def main():
 p=argparse.ArgumentParser()
 for n in ['arm','evidence101','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--mutation',choices=['cs','clock','miso','reset','order','call','baseline'])
 a=p.parse_args();s=a.arm.resolve()/'src';e=a.evidence101.resolve();o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
 m=json.loads((ROOT/'analysis/spi101-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 def write(n,t):(o/n).write_text(t,encoding='utf-8',newline='\n')
 shutil.copy2(__file__,o/'executed-test102.py');shutil.copy2(ROOT/'tests/nes-functional/quiesce102_model.c',o/'model.c')
 for n in ['nes_diag_runtime.c','nes_diag_runtime.h']:shutil.copy2(s/n,o/n)
 source=(s/'nes_diag_platform.c').read_text();write('production-platform102.c',source);write('production-snes.c',(s/'snes.c').read_text())
 write('snes102.inc',definition((s/'snes.c').read_text(),'snes_reset'))
 h=(e/'arm02/src/obj-nes-100/autoconf.h').read_text();cmsis=(s/'include/arm/ST/STM32F4/stm32f401xc.h').read_text()
 macros='\n'.join(x for x in h.splitlines() if re.match(r'#define (SET_BIT\(|CLEAR_BIT\(|GPIO_MODE_OUT\(|GPIO_MODE_IN\(|GPIO_DIR\(|FPGA_SSREG\s|FPGA_SSBIT\s|SNES_RESET_REG\s|SNES_RESET_BIT\s)',x))
 macros+='\n'+'\n'.join(re.findall(r'^#define (?:SPI_CR1_SPE|RCC_APB2RSTR_SPI1RST)(?:_Pos|_Msk)?\s[^\n]*',cmsis,re.M))+'\n';write('registers102.h',macros)
 q=helper(source);block=definition(source,'nes_diag_blocked');write('quiesce102-original.inc',definition(source,'nes_diag_spi_quiesce102'))
 if a.mutation=='cs':q=once(q,' SET_BIT(FPGA_SSREG,FPGA_SSBIT);',' /* removed CS deassert */')
 if a.mutation=='clock':q=once(q,' GPIO_MODE_OUT(GPIOB,3);',' /* removed SCK disconnect */')
 if a.mutation=='miso':q=once(q,' GPIO_MODE_IN(GPIOB,4);',' /* removed MISO input */')
 if a.mutation=='reset':q=once(q,' RCC->APB2RSTR |= RCC_APB2RSTR_SPI1RST;',' /* removed held reset */')
 if a.mutation=='order':q=once(q,' SET_BIT(FPGA_SSREG,FPGA_SSBIT);',' CLEAR_BIT(GPIOB,3); GPIO_MODE_OUT(GPIOB,3); step102(999); SET_BIT(FPGA_SSREG,FPGA_SSBIT);')
 if a.mutation=='call':block=once(block,' nes_diag_spi_quiesce102();',' /* no quiesce call */')
 if a.mutation=='baseline':
  old=e/'arm02/src/nes_diag_platform.c';assert sha(old)==json.loads((e/'manifest.json').read_bytes())['files']['arm02/src/nes_diag_platform.c']
  write('baseline101-platform.c',old.read_text());block=definition(old.read_text(),'nes_diag_blocked')
 write('quiesce102.inc',q);write('blocked102.inc',block)
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','model.c','nes_diag_runtime.c','-o','test.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,(o/'compile.log').read_text()
 cases=[0] if a.mutation else range(1024);results=[]
 for seed in cases:
  log=o/f'case-{seed:04}.log'
  with log.open('wb') as f:r=subprocess.run([str(o/'test.exe'),str(seed)],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=5)
  text=log.read_text(errors='replace')
  if a.mutation:assert r.returncode!=0 and 'Assertion' in text,text
  else:assert r.returncode==0 and 'PASS102' in text,text
  results.append(dict(seed=seed,exit=r.returncode,log_sha256=sha(log)))
 write('result.json',json.dumps(dict(cases=results,mutation=a.mutation,platform_sha256=sha(s/'nes_diag_platform.c'),config_sha256=sha(e/'arm02/src/obj-nes-100/autoconf.h'),physical=False,installable=False),indent=2)+'\n')
 print('PASS102 terminal cases='+str(len(results)))
if __name__=='__main__':main()
