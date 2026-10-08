# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_spi_boot import ROOT,sha
from nes_menu098 import once
from test_nes_menu098 import definition
from test_nes_quiesce102 import helper

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence101','arm','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--geometry96',action='store_true');a=p.parse_args();e=a.evidence101.resolve();s=a.arm.resolve()/'src';o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
 m=json.loads((ROOT/'analysis/spi101-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];source=e/('fat32-96-01' if a.geometry96 else 'main02');inputs={}
 def write(n,t):(o/n).write_text(t,encoding='utf-8',newline='\n')
 for f in source.rglob('*'):
  if f.is_file() and f.suffix in ['.c','.h','.inc','.packed','.raw','.bin','.nes']:
   key=f.relative_to(e).as_posix();assert sha(f)==pins[key];inputs[key]=sha(f);dst=o/f.relative_to(source);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
 shutil.copy2(__file__,o/'executed-main102.py');shutil.copy2(ROOT/'tools/test_nes_quiesce102.py',o/'executed-helper102.py');shutil.copy2(ROOT/'tests/nes-functional/quiesce102_main.inc',o/'quiesce-main102.inc')
 platform=(s/'nes_diag_platform.c').read_text();write('production-platform102.c',platform)
 # All101 main/lower source inputs are retained; replace only the blocked model.
 for n in ['memory.c','fpga_spi.c','fpga_spi.h','stm32f4xx/spi.c','stm32f4xx/spi.h']:
  assert (o/('production-'+n.replace('/','-'))).read_text()==(s/n).read_text(),n
 write('quiesce102-original.inc',definition(platform,'nes_diag_spi_quiesce102'));write('quiesce102.inc',helper(platform));write('blocked102.inc',definition(platform,'nes_diag_blocked'))
 reset=definition((s/'snes.c').read_text(),'snes_reset');write('snes102-original.inc',reset);write('snes102.inc',reset.replace('void snes_reset(','void actual_snes_reset102('))
 h=(e/'arm02/src/obj-nes-100/autoconf.h').read_text();macros='\n'.join(x for x in h.splitlines() if re.match(r'#define (SET_BIT\(|CLEAR_BIT\(|GPIO_MODE_OUT\(|GPIO_MODE_IN\(|GPIO_DIR\(|SNES_RESET_REG\s|SNES_RESET_BIT\s)',x))
 c=(s/'include/arm/ST/STM32F4/stm32f401xc.h').read_text();constants='\n'.join(re.findall(r'^#define (?:SPI_CR1_SPE|RCC_APB2RSTR_SPI1RST)(?:_Pos|_Msk)?\s[^\n]*',c,re.M))+'\n'
 write('gpio102.h',macros+'\n');write('constants102.h',constants)
 f=o/'mcu_loader_platform.h';t=f.read_text();t=once(t,'uint32_t MODER,ODR,IDR;','uint32_t MODER,ODR,IDR,OTYPER,BSRR;');t=once(t,'uint32_t SR,CR1;','uint32_t SR,CR1,CR2;');write(f.name,t)
 host=(o/'host100.c').read_text();host=once(host,definition(host,'nes_diag_blocked'),'')
 host=once(host,'#include "lower100.inc"','#include "lower100.inc"\n#include "quiesce-main102.inc"')
 host=once(host,'void snes_reset(int v){','void actual_snes_reset102(int);\nvoid snes_reset(int v){')
 host=once(host,' reset_held=v;',' reset_held=v;actual_snes_reset102(v);')
 host=once(host,' polls099=0;begin_lower100(baseline098);',' polls099=0;begin_lower100(baseline098);init102();')
 host=once(host,' if(baseline098){\n',' if(baseline098){\n  assert(terminal102==1);check_quiesce102();\n')
 host=host.replace('PASS100','PASS102');host='#include "constants102.h"\n'+host
 write('host102.c',host)
 sources=['card.c','host102.c','ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c']
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-ffunction-sections','-fdata-sections','-I.','-DGBC_SAVE_G12','-DGBC_DUMP_G12',*sources,'-Wl,--gc-sections','-o','host.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,(o/'compile.log').read_text(errors='replace')[-4000:]
 cases=[x['case'] for x in json.loads((source/'result.json').read_bytes())['cases']];results=[]
 for i,case in enumerate(cases):
  log=o/f'case-{i}.log';args=list(map(str,case))+[str(o/n) for n in ['fixture.nes','diag.packed','diag.raw','base.packed','base.raw','menu.bin']]
  with log.open('wb') as f:r=subprocess.run([str(o/'host.exe'),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  text=log.read_text(errors='replace');assert r.returncode==0 and 'PASS102' in text,text[-3000:]
  results.append(dict(case=case,exit=r.returncode,log_sha256=sha(log),last=text.strip().splitlines()[-1]))
 write('result.json',json.dumps(dict(cases=results,inputs=inputs,platform_sha256=sha(s/'nes_diag_platform.c'),geometry96=a.geometry96,physical=False,installable=False),indent=2)+'\n');print('PASS102 integrated main/blocked cases='+str(len(results)))
if __name__=='__main__':main()
