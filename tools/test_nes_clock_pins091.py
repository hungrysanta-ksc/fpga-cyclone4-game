# SPDX-License-Identifier: MIT
"""Run frozen090 session with actual GPIO helper bodies/macros and register model."""
from pathlib import Path
import argparse,json,re,shutil
from nes_spi_boot import ROOT,put,run,sha
from test_nes_clock_session090 import replace,fun
from nes_diag_recovery_checks import function
def main():
 p=argparse.ArgumentParser()
 for n in ['out','evidence090','gcc']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--mutation',choices=['no-af-restore','no-spi-restore','no-data-input'])
 a=p.parse_args();e=a.evidence090.resolve();o=a.out.resolve();assert not o.exists() and str(o).isascii()
 assert sha(e/'manifest.json')=='5ecbc6fe3f5580943d0a9d991d880595caa1d30db37cb78815114bc2c42f0512'
 pins=json.loads((e/'manifest.json').read_bytes())['files'];o.mkdir();inputs={}
 for n,h in pins.items():
  if n.startswith('host02/') and Path(n).suffix in ['.c','.h','.inc','.rbf']:
   assert sha(e/n)==h;d=o/n[7:];d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/n,d);inputs[n]=h
 def actual(n):
  k='arm01/source/src/'+n;assert sha(e/k)==pins[k];inputs[k]=pins[k];return (e/k).read_text()
 config=(o/'config.h').read_text().replace('struct gpio088 {uint32_t MODER,ODR,IDR;};','struct gpio088 {uint32_t MODER,ODR,IDR,AFR[2],PUPDR,OSPEEDR;};')
 config=config.replace('#endif\n\nstruct gpio088','\nstruct gpio088')
 config=replace(config,'#define BITBAND(r,p) ((p)==4?model_input():read_prog())','#define BITBAND(r,p) pin_read091(&(r),(p))')
 for old in ['#define FPGA_SEND_BYTE_SERIAL(b) send_byte(b)\n','#define FPGA_DIN_MASK() ((void)0)\n','#define FPGA_DIN_UNMASK() ((void)0)\n','#define FPGA_SSREG (&gpio_ss)\n','#define FPGA_SSBIT 0\n','#define FPGA_PROGBBIT 1\n','#define CCLK() model_cclk()\n']:config=replace(config,old,'')
 auto=actual('obj-report079/autoconf.h');fpga=actual('fpga.c');header=actual('fpga.h');spisrc=actual('stm32f4xx/spi.c')
 names=['IO_SPEED_H','GPIO_MODE_OUT','GPIO_MODE_IN','GPIO_MODE_AF','GPIO_PULLUP','GPIO_PULLNONE','GPIO_SPEED','FPGA_CCLKREG','FPGA_CCLKBIT','FPGA_PROGBREG','FPGA_PROGBBIT','FPGA_INITBREG','FPGA_INITBBIT','FPGA_DINREG','FPGA_DINBIT','FPGA_DONEREG','FPGA_DONEBIT','FPGA_SSREG','FPGA_SSBIT','FPGA_SEND_BYTE_SERIAL','SET_FPGA_DIN','FPGA_DIN_MASK','FPGA_DIN_UNMASK']
 macros=[]
 for n in names:
  # Capture continued lines explicitly; the greedy first line includes backslash.
  lines=auto[auto.index('#define '+n+' '):].splitlines() if '#define '+n+' ' in auto else auto[auto.index('#define '+n+'('):].splitlines()
  block=lines[0];i=0
  while lines[i].endswith('\\'):i+=1;block+='\n'+lines[i]
  macros.append(block)
 for n in ['SET_CCLK','CLR_CCLK','CCLK']:macros.append(next(l for l in header.splitlines() if l.startswith('#define '+n+'(')))
 st=actual('include/arm/ST/STM32F4/stm32f401xc.h')
 for name,value in [('MSTR',2),('BR',3),('SPE',6),('SSI',8),('SSM',9)]:assert re.search(r'^#define SPI_CR1_'+name+r'_Pos\s+\('+str(value)+r'U\)',st,re.M),name
 for pin in [3,4,5]:assert re.search(r'^#define GPIO_AFRL_AFSEL'+str(pin)+r'_Pos\s+\('+str(pin*4)+r'U\)',st,re.M)
 config+='\n#define GPIOA (&gpio_ss)\n#define GPIO_I IDR\n#define OUT_BIT(r,p,v) pin_out091(r,p,v)\n'+ '\n'.join(macros)+'\n'
 config+='''
#define SPI_CR1_SSM 512u
#define SPI_CR1_SSI 256u
#define SPI_CR1_MSTR 4u
#define SPI_CR1_BR_Pos 3u
#define GPIO_AFRL_AFSEL3_Pos 12u
#define GPIO_AFRL_AFSEL4_Pos 16u
#define GPIO_AFRL_AFSEL5_Pos 20u
void pin_out091(struct gpio088 *,unsigned,unsigned);
unsigned pin_read091(uint32_t *,unsigned);
#endif
'''
 put(o/'config.h',config)
 put(o/'bits.h','#define SET_BIT(r,p) model_set(r,p,1)\n#define CLEAR_BIT(r,p) model_set(r,p,0)\n')
 extracted=[]
 renames={'fpga_init':'pin_init091','fpga_postinit':'pin_post091','fpga_set_prog_b':'pin_prog091','fpga_set_cclk':'pin_cclk091','fpga_get_initb':'pin_status091','fpga_get_done':'pin_done091','spi_init':'pin_spi091'}
 for n,new in renames.items():
  raw=spisrc if n=='spi_init' else fpga
  start=re.search(r'^(?:void|int) '+n+r'\(',raw,re.M).start();body=function(raw[start:],n)
  for old,target in renames.items():body=re.sub(r'\b'+old+r'\b',target,body)
  extracted.append(body)
 put(o/'pins.c','#include "config.h"\n#include "bits.h"\nextern uint8_t SPI_OFFLOAD;\nvoid pin_cclk091(uint8_t);\n'+''.join(extracted))
 shutil.copy2(ROOT/'tests/nes-functional/clock_pins091.h',o/'pins-model.h')
 q=o/'probe-model.h';s=q.read_text();s=replace(s,'static unsigned shared_checks,prewrite_checks,writer_checks;','static unsigned shared_checks,prewrite_checks,writer_checks;\n#include "pins-model.h"')
 s=replace(s,'if(nes_return_failed())assert((r==&gpio_ss&&v)||(r==&gpio_b&&p==3&&!v));','if((r==GPIOB&&(p==8||p==9))||(r==GPIOA&&p==1)){pin_out091(r,p,v);return;}\n if(nes_return_failed())assert((r==&gpio_ss&&v)||(r==&gpio_b&&p==3&&!v));')
 s=replace(s,'assert(p==0);','assert(p==4);')
 s=replace(s,'if(!clock_ss&&!clock_sck&&v){','if(!clock_ss&&!clock_sck&&v){\n  assert(mode091(GPIOB,3)==1&&mode091(GPIOB,4)==0&&mode091(GPIOB,5)==1&&!(SPI1->CR1&SPI_CR1_SPE));')
 s=fun(s,'fpga_set_cclk','void fpga_set_cclk(uint8_t n){pin_cclk091(n);}')
 s=replace(s,'spi.CR1=0x345;spi.SR=SPI_SR_TXE;','spi.CR1=0;spi.SR=SPI_SR_TXE;pin_spi091();pin_bit091=pin_byte091=pin_edges091=pin_low091=0;pin_saved_modes091=GPIOB->MODER&0xfc0;')
 put(q,s)
 q=o/'platform-model.h';s=q.read_text()
 s=replace(s,'sent=clock_extra=0;}','sent=clock_extra=0;pin_init091();assert(mode091(GPIOB,8)==1&&mode091(GPIOB,9)==1&&mode091(GPIOA,1)==1&&mode091(GPIOA,15)==0&&mode091(GPIOB,7)==0);if(clock_cycle==3){assert(clock_ss&&SPI1->CR1==0x344&&(GPIOB->MODER&0xfc0)==pin_saved_modes091);}}')
 s=fun(s,'fpga_set_prog_b','void fpga_set_prog_b(uint8_t n){pin_prog091(n);}')
 s=fun(s,'fpga_get_initb','int fpga_get_initb(void){return pin_status091();}')
 s=fun(s,'fpga_get_done','int fpga_get_done(void){return pin_done091();}')
 s=replace(s,'postinit++;configured=1;','pin_post091();assert(mode091(GPIOB,8)==0);postinit++;configured=1;')
 s=replace(s,'io++;','bus_ready091();gpio_ss.ODR|=1u<<4;clock_ss=1;io++;')
 put(q,s)
 q=o/'session-tests.h';s=q.read_text();s=replace(s,'assert(!memcmp(rom,golden_boot,sizeof(rom)));inspect090(fat32,1);checks++;','assert(!memcmp(rom,golden_boot,sizeof(rom)));assert(pin_edges091==6543555&&pin_low091==pin_edges091);inspect090(fat32,1);checks++;');put(q,s)
 if a.mutation=='no-data-input':q=o/'pins.c';put(q,replace(q.read_text(),'GPIO_MODE_IN(FPGA_DINREG, FPGA_DINBIT); /* DATA0 -> MCU_RDY */','/* mutation: DATA0 remains output */'))
 if a.mutation in ['no-af-restore','no-spi-restore']:
  q=o/'nes_clock_reader088.c';s=q.read_text();old='GPIOB->MODER=(GPIOB->MODER&~MODE088)|mode088;' if a.mutation=='no-af-restore' else 'SPI1->CR1=cr1088;';put(q,replace(s,old,'/* omitted restore */'))
 shutil.copy2(__file__,o/'executed-driver091.py')
 names=['host.c','pins.c','ff.c','unicode/ccsbcs.c','rle.c','nes_diag_runtime.c','nes_menu_return.c','nes_sd_inventory_log.c','nes_report_checkpoint079.c','nes_report_disk081.c','nes_report_boot080.c','nes_report_decode080.c','nes_report_space084.c','nes_clock_config089.c','nes_clock_reader088.c','nes_clock_platform090.c','nes_clock_text090.c']
 run([a.gcc,'-std=c11','-D__USE_MINGW_ANSI_STDIO=1','-O2','-Wall','-Wextra','-Wno-format','-I.',*names,'-Wl,--wrap=nes_return_io_step','-Wl,--wrap=nes_return_log_allow','-o','host.exe'],o,'compile')
 try:log=run([o/'host.exe'],o,'host',300)
 except RuntimeError:
  if not a.mutation:raise
  log=(o/'host.log').read_text(errors='replace')
 if a.mutation:
  expected='mode091(GPIOB,8)==0' if a.mutation=='no-data-input' else 'clock_ss&&SPI1->CR1==0x344'
  assert 'Assertion failed' in log and expected in log,log[-1500:];result=dict(mutation=a.mutation,expected_failure=expected)
 else:assert 'PASS CLOCK_SESSION090 checks=94' in log;result=dict(checks=94)
 result.update(inputs=inputs,files={n:sha(o/n) for n in names},configuration_rising_edges_per_success=6543555,configuration_falling_edges_per_success=6543555,physical=False,production_changed=False)
 put(o/'result.json',json.dumps(result,indent=2)+'\n');print(log[-1900:])
if __name__=='__main__':main()
