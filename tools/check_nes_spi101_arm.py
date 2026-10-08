# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,re,subprocess
from nes_spi_boot import ROOT,sha
from test_nes_menu098 import definition

def main():
 p=argparse.ArgumentParser()
 for n in ['arm','phase','evidence100','objdump','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();s=a.arm/'src';e=a.evidence100
 meta=json.loads((ROOT/'analysis/lower100-verification.json').read_bytes());assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 for n in ['fpga_spi.h','main.c','memory.c','nes_menu_return.c','nes_diag_runtime.c','nes_diag_platform.c','stm32f4xx/uart.c','stm32f4xx/timer.c','stm32f4xx/rtc.c','stm32f4xx/sdnative.c']:
  assert sha(s/n)==pins['arm02/src/'+n],n
 old=(e/'arm02/src/stm32f4xx/spi.c').read_text();new=(s/'stm32f4xx/spi.c').read_text()
 for n in ['spi_tx_sync','nes_return_spi_exchange']:
  old=old.replace(definition(old,n),definition(new,n))
 assert old==new,'unexpected SPI changes'
 assert (a.phase/'production-stm32f4xx-spi.c').read_text()==new
 assert (a.phase/'production-nes_diag_platform.c').read_bytes()==(s/'nes_diag_platform.c').read_bytes()
 elf=s/'obj-nes-100/sd2snes.elf';fw=s/'obj-nes-100/firmware.stm';dumps={}
 for n in ['spi_tx_sync','nes_return_spi_exchange','nes_diag_blocked']:
  b=subprocess.check_output([str(a.objdump),'-d','--disassemble='+n,str(elf)])
  (a.arm/(n+'-checked101.txt')).write_bytes(b);dumps[n]=b.decode()
 for n in ['spi_tx_sync','nes_return_spi_exchange']:
  t=dumps[n];calls=list(re.finditer(r'\b(?:bl|b\.w)\s+[^\n]*<nes_return_spi_wait>',t));assert len(calls)==(2 if n=='spi_tx_sync' else 3)
  before=t[:calls[0].start()];between=t[calls[0].end():calls[1].start()]
  assert re.search(r'movs\s+r1, #1',before) and re.search(r'mov\s+r0, r1',before)
  assert re.search(r'(?:beq\.n|cbz)\s+r?0?,?',between) and re.search(r'movs\s+r1, #0',between) and re.search(r'movs\s+r0, #7',between)
 # This is a recorded remaining boundary, not a successful cancellation test.
 block=definition((s/'nes_diag_platform.c').read_text(),'nes_diag_blocked')
 assert 'snes_reset(1)' in block and 'for(;;)__NOP();' in block
 assert not any(x in block for x in ['SPI1','GPIO_MODE','FPGA_DESELECT'])
 assert '<snes_reset>' in dumps['nes_diag_blocked']
 result=dict(firmware_bytes=fw.stat().st_size,firmware_sha256=sha(fw),elf_sha256=sha(elf),changed_spi_functions=['spi_tx_sync','nes_return_spi_exchange'],platform_unchanged=sha(s/'nes_diag_platform.c'),legacy_source_unchanged=True,arm_order='TXE true; fault exit; BSY false',blocked_does_not_shutdown_spi=True,physical=False,installable=False)
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('PASS101 same-source ARM TXE-before-BSY; abort remains open')
if __name__=='__main__':main()
