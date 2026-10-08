# SPDX-License-Identifier: MIT
"""Source equality and actual RTC/main/FatFS call sites in the linked ARM."""
from pathlib import Path
import argparse,json,re,subprocess
from nes_spi_boot import sha,ROOT

def main():
 p=argparse.ArgumentParser()
 for n in ['arm','host','evidence098','objdump','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();s=a.arm/'src';e=a.evidence098
 meta=json.loads((ROOT/'analysis/menu098-verification.json').read_bytes());assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 for n in ['main.c','memory.c','memory.h','nes_menu_return.c','nes_diag_runtime.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c','ff.c','ffconf.h','stm32f4xx/sdnative.c','stm32f4xx/spi.c','stm32f4xx/uart.c','stm32f4xx/timer.c']:
  assert sha(s/n)==pins['arm01/src/'+n],n
 assert sha(s/'stm32f4xx/rtc.c')==sha(a.host/'rtc099-production.c')
 assert sha(s/'nes_diag_runtime.h')==sha(a.host/'nes_diag_runtime.h')
 assert (a.host/'main098.inc').read_bytes()==(e/'suite03/main098.inc').read_bytes()
 assert (a.host/'load098.inc').read_bytes()==(e/'suite03/load098.inc').read_bytes()
 elf=s/'obj-nes-099/sd2snes.elf';fw=s/'obj-nes-099/firmware.stm';d={}
 names=['rtc_wait099','read_rtc','set_rtc','get_bcdtime','get_fattime','set_bcdtime','main','f_open','f_sync']
 for n in names:
  b=subprocess.check_output([str(a.objdump),'-d','--disassemble='+n,str(elf)])
  (a.arm/(n+'-checked099.txt')).write_bytes(b);d[n]=b.decode().replace('\r\n','\n')
  assert '<'+n+'>:' in d[n],n
 for n in ['nes_diag_wait_start','nes_diag_wait_step','nes_return_io_step','nes_return_failed','nes_return_fail']:assert '<'+n+'>' in d['rtc_wait099']
 assert '#100' in d['rtc_wait099'] and '0x000186a0' in d['rtc_wait099'] and '#17' in d['rtc_wait099']
 for n in ['read_rtc','set_rtc']:assert '<rtc_wait099>' in d[n] and '<nes_diag_active>' in d[n]
 for n in ['get_bcdtime','get_fattime']:assert '<read_rtc>' in d[n] and '<nes_return_failed>' in d[n]
 assert '<set_rtc>' in d['set_bcdtime']
 for n in ['rtc_isvalid','get_bcdtime','set_bcdtime','invalidate_rtc','nes_menu_diagnostic_prepared','nes_menu_diagnostic_released']:assert '<'+n+'>' in d['main']
 assert '<get_fattime>' in d['f_open'] and '<get_fattime>' in d['f_sync']
 assert re.search(r'mov\.w\s+r1, #12582912[^\n]*\n[^\n]*\n[^\n]*<load_rom>',d['main'])
 # Failure cleanup: zero returned by wait is written to INIT alias and WPR,
 # then branches to return before the calendar write block (inspect raw dump).
 assert re.search(r'bl\s+[^\n]*<rtc_wait099>\n[^\n]*cbnz[^\n]*\n[^\n]*ldr[^\n]*\n[^\n]*str.w\s+r0, \[r7, #412\][^\n]*\n[^\n]*str\s+r0, \[r3, #36\]',d['set_rtc'])
 result=dict(firmware_bytes=fw.stat().st_size,firmware_sha256=sha(fw),elf_sha256=sha(elf),rtc_sha256=sha(s/'stm32f4xx/rtc.c'),runtime_header_sha256=sha(s/'nes_diag_runtime.h'),same_main_and_load=True,physical=False,installable=False)
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('PASS099 ARM RTC limits/cleanup/main/FatFS callsites and host source equality')
if __name__=='__main__':main()
