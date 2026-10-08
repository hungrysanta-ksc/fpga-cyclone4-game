# SPDX-License-Identifier: MIT
"""Verify tested full loader/address predicates and actual ARM call arguments."""
from pathlib import Path
import argparse,json,re,subprocess
from nes_spi_boot import sha,ROOT
from nes_menu098 import once
from test_nes_menu098 import definition

def main():
 p=argparse.ArgumentParser()
 for n in ['arm','host','evidence094','objdump','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();src=a.arm/'src';old=a.evidence094/'arm04/src'
 meta=json.loads((ROOT/'analysis/session094-verification.json').read_bytes());assert sha(a.evidence094/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((a.evidence094/'manifest.json').read_bytes())['files']
 for n in ['memory.c','nes_menu_return.c','main.c','memory.h']:
  assert sha(old/n)==pins['arm04/src/'+n]
 expected=once((old/'memory.c').read_text(),'||flags||base_addr)','||flags||base_addr!=SRAM_MENU_ADDR)')
 assert (src/'memory.c').read_text()==expected==(a.host/'memory.c').read_text()
 expected=once((old/'nes_menu_return.c').read_text(),'size==NES_MENU076_SIZE&&!offset&&!address;','size==NES_MENU076_SIZE&&!offset&&address==SRAM_MENU_ADDR;')
 assert (src/'nes_menu_return.c').read_text()==expected==(a.host/'nes_menu_return.c').read_text()
 assert (a.host/'load098.inc').read_text()==definition((src/'memory.c').read_text(),'load_rom')
 assert (a.host/'reliable098.inc').read_text()==definition((src/'memory.c').read_text(),'sram_reliable')
 retained=list(meta['host_arm_identical'])+['main.c','memory.h','nes_menu076.c','ff.c','cfg.c','snes.c','stm32f4xx/sdnative.c','stm32f4xx/spi.c','stm32f4xx/rtc.c','stm32f4xx/timer.c','stm32f4xx/uart.c']
 for n in retained:assert sha(src/n)==sha(old/n)==pins['arm04/src/'+n],n
 elf=src/'obj-nes-098/sd2snes.elf';fw=src/'obj-nes-098/firmware.stm';dumps={}
 for n in ['main','load_rom','nes_return_copy_menu']:
  b=subprocess.check_output([str(a.objdump),'-d','--disassemble='+n,str(elf)])
  (a.arm/(n+'-checked098.txt')).write_bytes(b);dumps[n]=b.decode()
 assert re.search(r'mov\.w\s+r1, #12582912[^\n]*\n[^\n]*\n[^\n]*<load_rom>',dumps['main'])
 for n in ['load_rom','nes_return_copy_menu']:
  assert re.search(r'cmp\.w\s+r\d+, #12582912\b',dumps[n]),n
 for n in ['sram_writeblock','sram_readblock','nes_menu_crc076','nes_return_failed']:
  assert '<'+n+'>' in dumps['nes_return_copy_menu']
 for n in ['nes_menu_classify076','nes_return_copy_menu','gbc_save_disarm','gbc_dump_disarm']:
  assert '<'+n+'>' in dumps['load_rom']
 for n in ['nes_menu_diagnostic_prepared','nes_menu_diagnostic_released','snes_reset','cfg_is_autoboot_enabled','status_load_to_menu']:
  assert '<'+n+'>' in dumps['main']
 result=dict(firmware_bytes=fw.stat().st_size,firmware_sha256=sha(fw),elf_sha256=sha(elf),host_arm_identical={n:sha(src/n) for n in ['memory.c','nes_menu_return.c']},retained094={n:sha(src/n) for n in retained},menu_destination=0xc00000,physical=False,installable=False)
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('PASS098 ARM actual main argument and two predicates 0xC00000; host/ARM sources match')
if __name__=='__main__':main()
