# SPDX-License-Identifier: MIT
"""Build actual MCU GPIO reader with modeled registers/time/MISO; retain trace."""
from pathlib import Path
import argparse,json,re,shutil
from nes_spi_boot import ROOT,put,run,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['out','gcc','runtime-source']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--trace-mode',choices=['active','absent'],default='active')
 p.add_argument('--mutation',choices=['no-pair-check','no-deadline','no-owner-check'])
 a=p.parse_args();out=a.out.resolve();assert str(out).isascii();out.mkdir(parents=True,exist_ok=False)
 for n in ['nes_clock_reader088.c','nes_clock_reader088.h']:shutil.copy2(ROOT/'src/nes/firmware'/n,out/n)
 if a.mutation:
  q=out/'nes_clock_reader088.c';s=q.read_text()
  if a.mutation=='no-pair-check':
   s=s.replace('memcmp(a+2,b+2,14)||((a[1]^b[1])&9)||((a[1]&4)&&!(b[1]&4))','false')
  if a.mutation=='no-deadline':
   s=s.replace('(uint32_t)(nes_diag_ticks()-report088->started)>=450','false').replace('out->elapsed>=450','false')
  if a.mutation=='no-owner-check':s=s.replace('&&get_snes_reset()','')
  q.write_text(s,encoding='utf-8',newline='\n')
 # Public baseline header predates the current SPI/TIMER/MENU extensions.
 runtime=a.runtime_source/'nes_diag_runtime.h'
 assert sha(runtime)=='7d3e03de277d13c279f6bee926d1efb562a582f1d77787174e06a9a0f03f87df'
 assert sha(a.runtime_source/'nes_menu_return.h')=='4c3cc8054b30ca0e7ee3973b79713a9c12ba7fe3d29d4a87da4f19c2f2d09daf'
 shutil.copy2(runtime,out/'nes_diag_runtime.h');shutil.copy2(a.runtime_source/'nes_menu_return.h',out/'nes_menu_return.h')
 shutil.copy2(ROOT/'tests/nes-functional/clock_reader088_host.c',out/'host.c');shutil.copy2(__file__,out/'executed-driver.py')
 put(out/'config.h','''#ifndef CONFIG088
#define CONFIG088
#include <stdint.h>
struct gpio088 {uint32_t MODER,ODR,IDR;};
struct spi088 {uint32_t CR1,SR;};struct nvic088 {uint32_t ISER[4];};
extern struct gpio088 gpio_b,gpio_ss;extern struct spi088 spi;extern struct nvic088 nvic;
#define GPIOB (&gpio_b)
#define FPGA_SSREG (&gpio_ss)
#define FPGA_SSBIT 0
#define SPI1 (&spi)
#define SPI_SR_BSY 128u
#define SPI_SR_TXE 2u
#define SPI_CR1_SPE 64u
#define NVIC (&nvic)
#define OTG_FS_IRQn 67u
void model_set(struct gpio088 *,unsigned,unsigned);unsigned model_input(void);
#endif
''')
 put(out/'bits.h','''#define SET_BIT(r,p) model_set(r,p,1)
#define CLEAR_BIT(r,p) model_set(r,p,0)
#define BITBAND(r,p) model_input()
''')
 put(out/'snes.h','int get_snes_reset(void);void snes_reset(int);\n');put(out/'fpga.h','int fpga_get_done(void);\n')
 run([a.gcc,'-std=c11','-D__USE_MINGW_ANSI_STDIO=1','-O2','-Wall','-Wextra','-Werror','-I.','host.c','nes_clock_reader088.c','-o','host.exe'],out,'build')
 try:log=run([out/'host.exe','wave.txt',a.trace_mode],out,'host',120)
 except RuntimeError:
  if not a.mutation:raise
  log=(out/'host.log').read_text(errors='replace')
 if a.mutation:
  expected={'no-pair-check':'case=7 mode=7','no-deadline':'time_us>=4500000&&time_us<4520000','no-owner-check':'want=0/5'}[a.mutation]
  assert 'Assertion failed' in log and expected in log
  put(out/'result.json',json.dumps(dict(candidate='NES-CLOCK-READER-088',mutation=a.mutation,expected_failure=expected,source_sha256=sha(out/'nes_clock_reader088.c')),indent=2)+'\n')
  print('EXPECTED C guard rejection '+a.mutation);return
 m=re.search(r'PASS CLOCK_READER088 tests=(\d+) normal_checks=(\d+) normal_frames=(\d+)',log);assert m
 put(out/'result.json',json.dumps(dict(candidate='NES-CLOCK-READER-088',tests=int(m[1]),normal_checks=int(m[2]),normal_frames=int(m[3]),sources={n:sha(out/n) for n in ['nes_clock_reader088.c','nes_clock_reader088.h','nes_diag_runtime.h','nes_menu_return.h','host.c']},wave_sha256=sha(out/'wave.txt'),trace_mode=a.trace_mode,actual_gpio_c=True,modeled_miso=True,hardware_execution=False,installable=False),indent=2)+'\n')
 print(m[0],flush=True)

if __name__=='__main__':main()
