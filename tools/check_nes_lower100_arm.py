# SPDX-License-Identifier: MIT
"""Check exact actual lower functions, retained sources and final ARM calls."""
from pathlib import Path
import argparse,json,re,subprocess
from nes_spi_boot import ROOT,sha
from test_nes_lower100 import MEM,FPGA,SPI
from test_nes_menu098 import definition

def main():
 p=argparse.ArgumentParser()
 for n in ['arm','host','evidence099','objdump','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();s=a.arm/'src';e=a.evidence099
 m=json.loads((ROOT/'analysis/rtc099-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];retained={}
 for n in ['main.c','memory.c','fpga_spi.c','nes_menu_return.c','nes_diag_runtime.c','nes_diag_runtime.h','nes_cf86_session094.c','nes_h1_stm32.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c','ff.c','stm32f4xx/rtc.c','stm32f4xx/uart.c','stm32f4xx/timer.c','stm32f4xx/sdnative.c']:
  assert sha(s/n)==pins['arm01/src/'+n],n;retained[n]=sha(s/n)
 equal={};line_endings={}
 for n in ['memory.c','fpga_spi.c','fpga_spi.h','stm32f4xx/spi.c','stm32f4xx/spi.h']:
  host=a.host/('production-'+n.replace('/','-'))
  assert (s/n).read_text()==host.read_text(),n
  equal[n]=sha(s/n)
  if sha(s/n)!=sha(host):line_endings[n]=dict(arm=sha(s/n),host_lf=sha(host))
 for file,names,inc in [('memory.c',MEM,'memory100.inc'),('stm32f4xx/spi.c',SPI,'spi100-original.inc')]:
  assert (a.host/inc).read_text()=='\n'.join(definition((s/file).read_text(),n) for n in names)
 assert (a.host/'fpga100.inc').read_text()=='uint16_t current_features;\n'+'\n'.join(definition((s/'fpga_spi.c').read_text(),n) for n in FPGA)
 assert (a.host/'main098.inc').read_bytes()==(e/'main04/main098.inc').read_bytes()
 assert (a.host/'load098.inc').read_bytes()==(e/'main04/load098.inc').read_bytes()
 elf=s/'obj-nes-100/sd2snes.elf';fw=s/'obj-nes-100/firmware.stm';d={}
 for n in ['main','load_rom','set_mcu_addr','sram_writeblock','sram_readblock','sram_readlong','sram_memset','nes_return_spi_wait','nes_return_spi_ready','nes_return_spi_exchange','spi_tx_byte','spi_rx_byte']:
  b=subprocess.check_output([str(a.objdump),'-d','--disassemble='+n,str(elf)])
  (a.arm/(n+'-checked100.txt')).write_bytes(b);d[n]=b.decode().replace('\r\n','\n');assert '<'+n+'>:' in d[n],n
 for n in ['nes_return_spi_wait','nes_return_spi_ready','nes_return_spi_exchange']:assert '<nes_return_io_step>' in d[n] and '<nes_return_failed>' in d[n],n
 assert '#25' in d['nes_return_spi_wait'] and '0x000f4240' in d['nes_return_spi_wait']
 for n in ['set_mcu_addr','sram_writeblock','sram_readblock','sram_readlong','sram_memset']:
  for call in ['spi_tx_sync','nes_diag_active','nes_return_failed']:assert '<'+call+'>' in d[n],(n,call)
 for n in ['sram_writeblock','sram_readblock','sram_readlong','sram_memset']:
  assert '<set_mcu_addr>' in d[n] and '<nes_return_spi_ready>' in d[n]
 assert '<spi_tx_byte>' in d['sram_writeblock'] and '<spi_rx_byte>' in d['sram_readblock']
 assert '<nes_return_spi_wait>' in d['spi_tx_byte'] and '<nes_return_spi_exchange>' in d['spi_rx_byte']
 for n in ['load_rom','get_bcdtime','set_bcdtime','snes_reset','nes_menu_diagnostic_prepared','nes_menu_diagnostic_released']:assert '<'+n+'>' in d['main']
 assert '<nes_return_copy_menu>' in d['load_rom']
 result=dict(firmware_bytes=fw.stat().st_size,firmware_sha256=sha(fw),elf_sha256=sha(elf),host_arm_normalized_identical=equal,host_lf_only=line_endings,retained099=retained,actual_functions=len(MEM)+len(FPGA)+len(SPI),physical=False,installable=False)
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('PASS100 actual lower functions/ARM callsites; RTC/main/load/native retained')
if __name__=='__main__':main()
