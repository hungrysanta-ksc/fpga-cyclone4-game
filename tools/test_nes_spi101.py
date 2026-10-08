# SPDX-License-Identifier: MIT
"""Compile actual SPI/runtime/blocked bodies against a delayed-start SPI model."""
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_spi_boot import ROOT,sha
from test_nes_menu098 import definition
from nes_menu098 import once

def main():
 p=argparse.ArgumentParser()
 for n in ['arm','out','gcc']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--mutation',choices=['sync','exchange','reverse','fault','baseline-sync','baseline-exchange'])
 p.add_argument('--evidence100',type=Path)
 a=p.parse_args();s=a.arm.resolve()/'src';o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
 def write(n,t):(o/n).write_text(t,encoding='utf-8',newline='\n')
 shutil.copy2(__file__,o/'executed-test101.py');shutil.copy2(ROOT/'tests/nes-functional/spi101_model.c',o/'model.c')
 pins={}
 for n in ['stm32f4xx/spi.c','nes_menu_return.c','nes_diag_runtime.c','nes_diag_runtime.h','fpga_spi.h','nes_diag_platform.c']:
  shutil.copy2(s/n,o/('production-'+n.replace('/','-')));pins[n]=sha(s/n)
 for n in ['nes_diag_runtime.c','nes_diag_runtime.h']:shutil.copy2(s/n,o/n)
 c=(s/'include/arm/ST/STM32F4/stm32f401xc.h').read_text()
 write('cmsis101.h','\n'.join(re.findall(r'^#define SPI_SR_\w+[^\n]*',c,re.M))+'\n')
 names=['nes_return_reset','nes_return_io_begin','nes_return_io_step','nes_return_fail','nes_return_failed','nes_return_log_allow']
 ret='static bool fault,log_allowed,io_active;\nstatic struct nes_diag_wait io_wait;\n'+'\n'.join(definition((s/'nes_menu_return.c').read_text(),n) for n in names)
 write('return101.inc',ret)
 spi_source=(s/'stm32f4xx/spi.c').read_text()
 if a.mutation and a.mutation.startswith('baseline-'):
  e=a.evidence100;meta=json.loads((ROOT/'analysis/lower100-verification.json').read_bytes());assert sha(e/'manifest.json')==meta['manifest_sha256']
  key='arm02/src/stm32f4xx/spi.c';assert sha(e/key)==json.loads((e/'manifest.json').read_bytes())['files'][key]
  spi_source=(e/key).read_text();write('baseline100-spi.c',spi_source)
 spi='\n'.join(definition(spi_source,n) for n in ['nes_return_spi_wait','nes_return_spi_exchange','spi_tx_sync','spi_tx_byte','spi_txrx_byte'])
 write('spi101-original.inc',spi)
 if a.mutation=='sync':spi=once(spi,'if(nes_return_spi_wait(SPI_SR_TXE_Pos,true))\n','if(true)\n')
 if a.mutation=='exchange':spi=once(spi,' if(!nes_return_spi_wait(SPI_SR_TXE_Pos,true))return 0;\n','')
 if a.mutation=='reverse':spi=once(spi,'if(nes_return_spi_wait(SPI_SR_TXE_Pos,true))\n      (void)nes_return_spi_wait(SPI_SR_BSY_Pos,false);','if(nes_return_spi_wait(SPI_SR_BSY_Pos,false))\n      (void)nes_return_spi_wait(SPI_SR_TXE_Pos,true);')
 if a.mutation=='fault':spi=spi.replace('nes_return_failed()||!nes_return_io_step()','false')
 spi=re.sub(r'SPI1->DR\s*=\s*([^;]+);',r'write_dr101(\1);',spi).replace('SPI1->DR','read_dr101()')
 write('spi101.inc',spi)
 h=(s/'fpga_spi.h').read_text();write('select101.h','\n'.join(x for x in h.splitlines() if x.startswith(('#define FPGA_SELECT(', '#define FPGA_DESELECT(', '#define FPGA_TX_SYNC(')))+'\n')
 write('blocked101.inc',definition((s/'nes_diag_platform.c').read_text(),'nes_diag_blocked'))
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','model.c','nes_diag_runtime.c','-o','test.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,(o/'compile.log').read_text()
 cases=[(t,d,c,phase) for t in [0,1] for d in [0,1,2] for c in [16,32] for phase in range(c+d+2)]
 cases += [(2,2,16,0)]+[(t,2,16,0) for t in range(3,14)]
 if a.mutation:cases=[(1 if a.mutation in ['exchange','baseline-exchange'] else 9 if a.mutation=='fault' else 0,2,16,0)]
 results=[]
 for i,case in enumerate(cases):
  log=o/f'case-{i:03}.log'
  with log.open('wb') as f:r=subprocess.run([str(o/'test.exe'),*map(str,case)],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=20)
  t=log.read_text(errors='replace')
  if a.mutation:assert r.returncode!=0 and 'Assertion' in t,t
  else:assert r.returncode==0 and 'PASS101' in t,t
  results.append(dict(case=case,exit=r.returncode,log_sha256=sha(log),last=t.strip().splitlines()[-1]))
 write('result.json',json.dumps(dict(cases=results,production=pins,mutation=a.mutation,physical=False,installable=False),indent=2)+'\n')
 print('PASS101 delayed-start cases='+str(len(results)))
if __name__=='__main__':main()
