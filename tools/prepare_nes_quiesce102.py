# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil
from nes_spi_boot import ROOT,sha
from nes_menu098 import once

HELPER='''/* Terminal-only cancellation. Discard the partial command; never resume.
 * No status, timer, UART, SPI transaction or DMA completion wait is allowed.
 * CS precedes the GPIO mux change; preload idle latches before output mode.
 * SPI1 reset remains asserted until external reset/power cycle.
 * CPU/bus/GPIO execution and the established board pin mapping are assumed. */
static void nes_diag_spi_quiesce102(void) __attribute__((noinline));
static void nes_diag_spi_quiesce102(void) {
 SET_BIT(FPGA_SSREG,FPGA_SSBIT);
 FPGA_SSREG->OTYPER &= ~(1u<<FPGA_SSBIT);
 GPIO_MODE_OUT(FPGA_SSREG,FPGA_SSBIT);
 __DSB();
 CLEAR_BIT(GPIOB,3);
 CLEAR_BIT(GPIOB,5);
 GPIOB->OTYPER &= ~((1u<<3)|(1u<<5));
 GPIO_MODE_OUT(GPIOB,3);
 GPIO_MODE_OUT(GPIOB,5);
 GPIO_MODE_IN(GPIOB,4);
 __DSB();
 SPI1->CR2=0;
 SPI1->CR1 &= ~SPI_CR1_SPE;
 RCC->APB2RSTR |= RCC_APB2RSTR_SPI1RST;
 __DSB();
}
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence101',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 e=a.evidence101.resolve();o=a.out.resolve();assert not o.exists()
 m=json.loads((ROOT/'analysis/spi101-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];copied={}
 for key,h in pins.items():
  if not key.startswith('arm02/'):continue
  n=key.removeprefix('arm02/');parts=Path(n).parts
  if any(x.startswith(('obj-','.dep-')) or x in ['db','incremental_db','output_files'] for x in parts):continue
  if Path(n).suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or Path(n).name=='.ARG_VERSION':continue
  assert sha(e/key)==h,key;d=o/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/key,d);copied[n]=h
 f=o/'src/nes_diag_platform.c';s=f.read_text()
 s=once(s,'void nes_diag_blocked(void) {',HELPER+'\nvoid nes_diag_blocked(void) {')
 s=once(s,' NVIC_DisableIRQ(OTG_FS_IRQn);snes_reset(1);',' NVIC_DisableIRQ(OTG_FS_IRQn);snes_reset(1);\n nes_diag_spi_quiesce102();')
 s=once(s,' * External power/reset intervention remains necessary; not pad cancellation. */',' * SPI1 stays in reset; external power/reset intervention is required. */')
 f.write_text(s,encoding='utf-8',newline='\n')
 (o/'src/VERSION').write_text('RELEASE_VERSION = "CF86-STOP102"\n',encoding='utf-8')
 changed={n:sha(o/n) for n,h in copied.items() if sha(o/n)!=h};assert set(changed)=={'src/nes_diag_platform.c','src/VERSION'},changed
 shutil.copy2(__file__,o/'executed-prepare102.py')
 (o/'preparation102.json').write_text(json.dumps(dict(baseline_manifest_sha256=sha(e/'manifest.json'),copied=copied,changed=changed,physical=False,installable=False),indent=2)+'\n',encoding='utf-8')
 print('PASS102 prepared terminal SPI cancellation; platform/VERSION only')
if __name__=='__main__':main()
