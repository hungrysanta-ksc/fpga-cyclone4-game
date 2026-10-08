# SPDX-License-Identifier: MIT
"""Actual main/RTC/SRAM/FPGA commands/SPI with register/byte responder seams."""
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_spi_boot import ROOT,sha
from nes_menu098 import once
from test_nes_menu098 import definition

MEM=['sram_writebyte','sram_readbyte','sram_writelong','sram_readlong','sram_readblock','sram_writeblock','sram_memset']
FPGA=['set_mcu_addr','set_bsx_regs','set_rom_mask','set_mapper','set_saveram_mask','set_saveram_base','fpga_set_features','fpga_set_213f','fpga_set_chipfeat','fpga_set_dac_boost','fpga_dspx_reset','fpga_reset_srtc_state','fpga_write_cheat','dac_pause','dac_reset','set_fpga_time']
SPI=['nes_return_spi_wait','nes_return_spi_exchange','nes_return_spi_ready','spi_tx_sync','spi_tx_byte','spi_rx_byte','spi_txrx_byte','spi_tx_block','spi_rx_block']

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence099','arm','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--unit',action='store_true');p.add_argument('--geometry96',action='store_true')
 p.add_argument('--mutation',choices=['select','async','budget','drain','ready','baseline'])
 a=p.parse_args();o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
 shutil.copy2(__file__,o/'executed-driver.py')
 e=a.evidence099.resolve();meta=json.loads((ROOT/'analysis/rtc099-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256'];pins=json.loads((e/'manifest.json').read_bytes())['files'];inputs={}
 source=e/('fat32-96-01' if a.geometry96 else 'main04')
 def write(n,s):(o/n).write_text(s,encoding='utf-8',newline='\n')
 for f in source.rglob('*'):
  if f.is_file() and f.suffix in ['.c','.h','.inc','.packed','.raw','.bin','.nes']:
   key=f.relative_to(e).as_posix();assert sha(f)==pins[key];inputs[key]=sha(f)
   d=o/f.relative_to(source);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,d)
 src=a.arm/'src'
 # Full source snapshots and exact extracted functions, before MMIO seams.
 originals={n:(src/n).read_text() for n in ['memory.c','fpga_spi.c','fpga_spi.h','stm32f4xx/spi.c','stm32f4xx/spi.h']}
 if a.mutation=='baseline':
  for n in ['fpga_spi.h','stm32f4xx/spi.c']:
   key='arm01/src/'+n;assert sha(e/key)==pins[key];originals[n]=(e/key).read_text()
 for n,s in originals.items():write('production-'+n.replace('/','-'),s)
 h=originals['fpga_spi.h'];h=re.sub(r'^#include[^\n]*\n','',h,flags=re.M)
 h=h.replace('uint8_t fpga_test(void);','')
 if a.mutation in ['select','async']:
  name='FPGA_SELECT()' if a.mutation=='select' else 'FPGA_SELECT_ASYNC()'
  line=next(x for x in h.splitlines() if x.startswith('#define '+name))
  h=once(h,line,line.replace('if(!nes_diag_active()||!nes_return_failed())',''))
 write('fpga100.h',h)
 write('spi100.h',re.sub(r'^#include[^\n]*\n','',originals['stm32f4xx/spi.h'],flags=re.M))
 c=src/'include/arm/ST/STM32F4/stm32f401xc.h'
 write('cmsis100.h','\n'.join(re.findall(r'^#define (?:SPI_SR_|DMA_LIFCR_|DMA_SxCR_|DMA_LISR_|SPI_CR2_)\w+[^\n]*',c.read_text(),re.M))+'\n')
 spi='\n'.join(definition(originals['stm32f4xx/spi.c'],n) for n in SPI)
 write('spi100-original.inc',spi)
 if a.mutation=='budget':spi=spi.replace('nes_return_failed()||!nes_return_io_step()','nes_return_failed()')
 if a.mutation=='drain':spi=once(spi,'  if(nes_return_failed()||!nes_return_io_step())return 0;\n','')
 if a.mutation=='ready':
  f=definition(spi,'nes_return_spi_ready');spi=once(spi,f,f.replace('nes_return_failed()||!nes_return_io_step()','nes_return_failed()'))
 # DR assignments/reads get explicit byte side effects. DMA references compile
 # but are unreachable during diagnostic ownership, not executed evidence.
 spi=spi.replace('&SPI1->DR','&dummy_dr100').replace('SPI1->CR2','dummy_cr2100')
 spi=spi.replace('BITBAND(dummy_cr2100, SPI_CR2_RXDMAEN_Pos)','dummy_cr2100')
 spi=re.sub(r'SPI1->DR\s*=\s*([^;]+);',r'write_dr100(\1);',spi)
 spi=spi.replace('SPI1->DR','read_dr100()').replace('SPI1->SR','status100()').replace('FPGA_MCU_RDY_REG->GPIO_I','ready100()')
 write('spi100.inc',spi)
 for f in ['lower100_model.h','lower100_unit.inc']:shutil.copy2(ROOT/'tests/nes-functional'/f,o/f)
 declarations='\n'.join(definition(originals['memory.c'],n).split('{',1)[0]+';' for n in MEM)
 write('memory100.inc','\n'.join(definition(originals['memory.c'],n) for n in MEM))
 write('fpga100.inc','uint16_t current_features;\n'+'\n'.join(definition(originals['fpga_spi.c'],n) for n in FPGA))
 lower='''#include "spi100.h"
#include "fpga100.h"
#include "cmsis100.h"
'''+declarations+'''
#undef SET_BIT
#undef CLEAR_BIT
#define SET_BIT(p,b) cs_pin100(p,b,true)
#define CLEAR_BIT(p,b) cs_pin100(p,b,false)
#undef BITBAND
#define BITBAND(r,p) (((r)>>(p))&1u)
#define SPI_REGS SPI1
#define SPI_SR SR
#define SPI_TFE SPI_SR_TXE_Pos
#include "lower100_model.h"
#include "spi100.inc"
#include "fpga100.inc"
#include "memory100.inc"
#include "lower100_unit.inc"
'''
 write('lower100.inc',lower)
 prefix=(o/'host098-prefix.inc').read_text().replace('#include "ready.inc"','')
 prefix=once(prefix,'native_ns096+=1000;return clock096();','native_ns096+=step_ns100;return clock096();')
 write('host098-prefix.inc','static unsigned step_ns100=1000;\n'+prefix)
 model=(o/'lower100_model.h').read_text().replace('static uint32_t step_ns100=1000;','')
 write('lower100_model.h',model)
 host=(o/'host099.c').read_text()
 for n in ['set_mcu_addr','set_bsx_regs']:host=host.replace('#define '+n+'(...) forbidden098()','')
 for n in FPGA:host=re.sub(r'^MODEL_VOID\('+n+r',[^\n]+\n','',host,flags=re.M)
 start=host.index('uint16_t sram_writeblock(');end=host.index('#include "reliable098.inc"',start)
 host=host[:start]+'#include "lower100.inc"\n'+host[end:]
 host=once(host,'native_ns096=ns=0;poll096=0;measured096=1;','native_ns096=ns=0;poll096=0;measured096=1;\n if(baseline098>=1000){run_unit100(baseline098-1000);return 0;}')
 start=host.index(' polls099=0;');end=host.index(' if(scenario098>=20)',start)
 host=host[:start]+''' polls099=0;begin_lower100(baseline098);
 if(scenario098==1)regs099[R_BKP0R]=0;
 if(baseline098==14)stall099=1;
'''+host[end:]
 start=host.index(' if(baseline098&&baseline098!=5)');end=host.index('\n else if(',start)
 host=host[:start]+''' if(baseline098){
  assert(!ok&&blocked098&&nes_return_failed()&&!irq&&reset_held&&cs100);
  assert(release097==(baseline098==13?1u:0u));
  assert_quiet100();
 }'''+host[end:]
 host=host.replace('PASS099','PASS100')
 host=host.replace('commands=%u\\n",scenario098','commands=%u tx=%u select=%u reads=%u\\n",scenario098').replace('nes_diag_status()->error,card_commands096());return 0;','nes_diag_status()->error,card_commands096(),tx100,select100,memreads100);return 0;')
 write('host100.c',host)
 sources=['card.c','host100.c','ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c']
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-ffunction-sections','-fdata-sections','-I.','-DGBC_SAVE_G12','-DGBC_DUMP_G12',*sources,'-Wl,--gc-sections','-o','host.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:
  text=(o/'compile.log').read_text(errors='replace');raise RuntimeError('\n'.join(x for x in text.splitlines() if 'error:' in x or 'undefined' in x))
 unitcases={'select':6,'async':6,'budget':7,'drain':10,'ready':8,'baseline':6}
 cases=[(0,1000+unitcases[a.mutation])] if a.mutation else [(0,1000+i) for i in range(13)] if a.unit else [(13,0),(0,9),(0,13)] if a.geometry96 else [(0,0),(1,0)]+[(0,i) for i in range(1,17)]
 results=[]
 for i,case in enumerate(cases):
  log=o/f'case-{i}.log';args=[str(x) for x in case]+[str(o/n) for n in ['fixture.nes','diag.packed','diag.raw','base.packed','base.raw','menu.bin']]
  with log.open('wb') as f:r=subprocess.run([str(o/'host.exe'),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  text=log.read_text(errors='replace')
  if a.mutation:assert r.returncode!=0 and 'Assertion' in text,text[-2500:]
  else:assert r.returncode==0 and 'PASS100' in text,text[-2500:]
  results.append(dict(case=case,exit=r.returncode,log_sha256=sha(log),last=text.strip().splitlines()[-1]))
 write('result.json',json.dumps(dict(unit=a.unit,geometry96=a.geometry96,mutation=a.mutation,inputs=inputs,production={n:sha(o/('production-'+n.replace('/','-'))) for n in originals},cases=results,physical=False,installable=False),indent=2)+'\n')
 print('PASS100 cases='+str(len(results)))
if __name__=='__main__':main()
