# SPDX-License-Identifier: MIT
"""Real089 configuration +088 reader +084 mini + shared runtime.
GPIO/status, SRAM, elapsed CPU time and SPI responses are modeled. No SD calls.
"""
from pathlib import Path
import argparse,json,re,shutil
from nes_spi_boot import ROOT,put,run,sha
PIN='1a43873e74e8a5cc888d099874d9ff17caa6959b4b12ffdd53a9d0987100a3d5'

def main():
 p=argparse.ArgumentParser()
 for n in ['out','gcc','evidence084','assembly']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--mutation',choices=['no-preflight-crc','no-stream-status','per-byte-budget','no-shared-guard'])
 a=p.parse_args();o=a.out.resolve();e=a.evidence084.resolve();assert str(o).isascii() and sha(e/'manifest.json')==PIN
 o.mkdir(parents=True,exist_ok=False);m=json.loads((e/'manifest.json').read_bytes())['files'];inputs={}
 def copy(n,target=None):
  k='work/arm-01/source/src/'+n;assert sha(e/k)==m[k];inputs[k]=m[k];shutil.copy2(e/k,o/(target or n))
 for n in ['nes_diag_runtime.c','nes_diag_runtime.h','nes_menu_return.c','nes_menu_return.h','nes_menu076.h','smc.h','nes_report_boot080.c','nes_report_boot080.h','nes_report_decode080.c','nes_report_layout084.h','snesboot.h']:copy(n)
 copy('obj-report079/cfgware.h','cfgware.h');copy('obj-report079/autoconf.h','input-autoconf.h')
 q=o/'nes_menu_return.c';s=q.read_text();put(q,s[:s.index('uint32_t nes_return_copy_menu(')])
 for n in ['nes_clock_config089.c','nes_clock_config089.h','nes_clock_reader088.c','nes_clock_reader088.h']:shutil.copy2(ROOT/'src/nes/firmware'/n,o/n)
 q=o/'nes_clock_config089.c';s=q.read_text()
 if a.mutation=='no-preflight-crc':s=s.replace('(s.crc^0xffffffffu)!=image->crc||!guard089()','false||!guard089()',1)
 if a.mutation=='no-stream-status':s=s.replace('s->send&&!fpga_get_initb()','false')
 if a.mutation=='per-byte-budget':s=s.replace('!(s->bytes&31u)','true')
 if a.mutation=='no-shared-guard':s=s.replace('||!nes_return_io_step()','')
 put(q,s)
 meta=json.loads((a.assembly/'result089.json').read_bytes())
 for n,key in [('clock089_payload.h','payload_header_sha256'),('output_files/board.rbf','rbf_sha256')]:assert sha(a.assembly/n)==meta[key],n
 shutil.copy2(a.assembly/'clock089_payload.h',o/'clock089_payload.h');shutil.copy2(a.assembly/'output_files/board.rbf',o/'golden.rbf')
 # Exact pinned STM32 LSB-first eight-bit transfer macro, endpoints instrumented.
 raw=(o/'input-autoconf.h').read_text();start=raw.index('#define FPGA_SEND_BYTE_SERIAL');end=raw.index('\n\n',start);macro=raw[start:end]
 put(o/'config.h','''#ifndef CONFIG089
#define CONFIG089
#include <stdint.h>
#include <stdbool.h>
struct gpio088 {uint32_t MODER,ODR,IDR;};
struct spi088 {uint32_t CR1,SR;};struct nvic088 {uint32_t ISER[4];};
extern struct gpio088 gpio_b,gpio_ss;extern struct spi088 spi;extern struct nvic088 nvic;
#define GPIOB (&gpio_b)
#define FPGA_SSREG (&gpio_ss)
#define FPGA_SSBIT 0
#define FPGA_PROGBBIT 1
#define SPI1 (&spi)
#define SPI_SR_BSY 128u
#define SPI_SR_TXE 2u
#define SPI_CR1_SPE 64u
#define NVIC (&nvic)
#define OTG_FS_IRQn 67u
void model_set(struct gpio088 *,unsigned,unsigned);unsigned model_input(void);
void model_din(unsigned);void model_cclk(void);unsigned read_prog(void);
#define SET_FPGA_DIN(n) model_din(n)
#define CCLK() model_cclk()
#define FPGA_DIN_MASK() ((void)0)
#define FPGA_DIN_UNMASK() ((void)0)
'''+macro+'\n#endif\n')
 put(o/'bits.h','''#define SET_BIT(r,p) model_set(r,p,1)
#define CLEAR_BIT(r,p) model_set(r,p,0)
#define BITBAND(r,p) ((p)==4?model_input():read_prog())
''')
 put(o/'fpga.h','''#include <stdint.h>
#define FPGA_ROM ((const uint8_t*)"rom")
void fpga_init(void);void fpga_set_prog_b(uint8_t);void fpga_set_cclk(uint8_t);
int fpga_get_initb(void);int fpga_get_done(void);void fpga_postinit(void);
''')
 put(o/'snes.h','uint8_t get_snes_reset(void);void snes_reset(int);\n')
 put(o/'fileops.h','/* no file IO in089 */\n')
 put(o/'memory.h','''#define SRAM_MENU_ADDR 0xc00000u
#define SRAM_CMD_ADDR 0xff1000u
uint16_t sram_writeblock(void *,uint32_t,uint16_t);uint16_t sram_readblock(void *,uint32_t,uint16_t);
''')
 put(o/'fpga_spi.h','void set_saveram_mask(uint32_t);void set_rom_mask(uint32_t);void set_mapper(uint8_t);\n')
 shutil.copy2(ROOT/'tests/nes-functional/clock_config089_host.c',o/'host.c');shutil.copy2(__file__,o/'executed-driver.py')
 source=['host.c','nes_clock_config089.c','nes_clock_reader088.c','nes_diag_runtime.c','nes_menu_return.c','nes_report_boot080.c','nes_report_decode080.c']
 run([a.gcc,'-std=c11','-D__USE_MINGW_ANSI_STDIO=1','-O2','-Wall','-Wextra','-Werror','-I.',*source,'-Wl,--wrap=nes_return_io_step','-o','host.exe'],o,'compile')
 try:log=run([o/'host.exe',o/'golden.rbf'],o,'host',180)
 except RuntimeError:
  if not a.mutation:raise
  log=(o/'host.log').read_text(errors='replace')
 if a.mutation:
  assert 'Assertion failed' in log
  expected={'no-preflight-crc':'!sent&&!prog','no-stream-status':'sent==positions[i]','per-byte-budget':'nes_clock_config089(&image)','no-shared-guard':'!nes_clock_config089(&image)&&nes_return_failed()'}[a.mutation]
  assert expected in log,log[-1500:]
  result=dict(mutation=a.mutation,expected_failure=expected)
 else:
  match=re.search(r'PASS CONFIG089 tests=(\d+) config_checks=(\d+)',log);assert match,log[-2000:]
  combined=[dict(zip(['mode','mini_checks','config_checks','through_reader','total_checks','frames','time_us'],map(int,row))) for row in re.findall(r'COMBINED089 mode=(\d+) mini_checks=(\d+) config_checks=(\d+) through_reader=(\d+) total_checks=(\d+) frames=(\d+) time_us=(\d+)',log)]
  assert len(combined)==3
  result=dict(tests=int(match[1]),config_checks=int(match[2]),combined=combined,assembly_sha256=sha(a.assembly/'result089.json'))
 result.update(inputs=inputs,source_hashes={n:sha(o/n) for n in source},original_macro_sha256=sha(o/'input-autoconf.h'),physical=False,linked_firmware=False,sd_session=False)
 put(o/'result.json',json.dumps(result,indent=2)+'\n');print(log[-1500:],flush=True)
if __name__=='__main__':main()
