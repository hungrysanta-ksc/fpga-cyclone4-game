# SPDX-License-Identifier: MIT
"""064 scoped recoverable read/configuration, derived from unchanged062.

The platform is supplied explicitly: no private snapshot is distributed.
Legacy function bodies are retained with diagnostic-only guards.
"""
from pathlib import Path
import json,shutil,argparse
from nes_menu_diagnostic import source as source062,materialize as materialize062,replace
from nes_mcu_loader import FW,sha
PINNED={
 'fpga.c':'555797396be0ffe632def409d2521e898f09e4dd90cf3399fb952a79b53fb90f',
 'stm32f4xx/led.c':'b83fabab92836ef9952b1f257bba9ec325fc6fa91ce5c044489929e9b47bc81d',
 'stm32f4xx/sdnative.c':'a7324f8fc7e407181fe0c52db9e50a7c3128447450f84c3ba30d673686c44390',
 'stm32f4xx/uart.c':'447c4d85cc17d5863434889185eef108ee2c0f8bb0085118ac935d2c21d2f976',
 'stm32f4xx/timer.c':'5b14f38360ea355687f5511bffcc73365f2ec3c0070526836a47b8a165b7adbf',
 'stm32f4xx/timer.h':'99cd295b535945b97ccf16cb5ac0f9e9c92e89d9cbea4742bfd7b5db7c560ff4',
 'config-mk3-stm32':'b2f4986384e22304f9819e5497746136c4969d06467665abbf20da2b9643728f'}

def source():
 s=source062()
 s=replace(s,'#include "nes_menu_probe.h"','#include "nes_menu_probe.h"\n#include "nes_diag_runtime.h"')
 # Only060/062 probe, not frozen044/056 functions, receives the new path.
 at=s.index('bool nes_menu_sd_probe(');prefix=s[:at];body=s[at:]
 body=replace(body,' snes_reset(1);',' snes_reset(1);\n nes_diag_sd_reset();nes_diag_begin();')
 body=replace(body,' /* fpga_pgm uses its global handle; our independent read-only FIL remains\n  * open. It may enter the existing platform panic on hardware failures. */',' /* Independent checked programmer; errors return to protected recovery. */')
 body=replace(body,' fpga_pgm((uint8_t *)image);\n if(!configured(image))',
  ' nes_diag_progress(NES_DIAG_CONFIG,0,0);\n if(!nes_diag_fpga_pgm((const uint8_t *)image)||!configured(image))')
 body=replace(body,'  crc=load_crc(crc,buffer,sizeof(buffer));','  crc=load_crc(crc,buffer,sizeof(buffer));\n  nes_diag_progress(NES_DIAG_VALIDATE,offset+sizeof(buffer),total);',2)
 # Second occurrence is DATA, not validation.
 last=body.rfind('  nes_diag_progress(NES_DIAG_VALIDATE,offset+sizeof(buffer),total);')
 body=body[:last]+body[last:].replace('  nes_diag_progress(NES_DIAG_VALIDATE,offset+sizeof(buffer),total);','  nes_diag_progress(NES_DIAG_LOAD,offset,total);',1)
 body=replace(body,'   r->acknowledged_bytes=offset+i+1;\n  }\n }','   r->acknowledged_bytes=offset+i+1;\n  }\n  nes_diag_progress(NES_DIAG_LOAD,offset+sizeof(buffer),total);\n }')
 body=replace(body,' r->end_accepted=true;',' r->end_accepted=true;\n nes_diag_progress(NES_DIAG_CHECK,0,total);')
 body=replace(body,' report->verified=true;',' report->verified=true;\n nes_diag_progress(NES_DIAG_CHECK,total,total);')
 body=replace(body,'  fpga_pgm((uint8_t *)FPGA_BASE);\n  if(!configured((const char *)FPGA_BASE)',
  '  nes_diag_progress(NES_DIAG_RECOVER,0,0);\n  if(!nes_diag_fpga_pgm((const uint8_t *)FPGA_BASE)||!configured((const char *)FPGA_BASE)')
 body=replace(body,' slow_end();\n if(changed_fpga)',
  ' slow_end();\n if(nes_diag_sd_failed()){nes_diag_progress(NES_DIAG_BLOCKED,0,0);return false;}\n if(changed_fpga)')
 body=replace(body,'fpga_test()!=FPGA_TEST_TOKEN)return false;','fpga_test()!=FPGA_TEST_TOKEN){nes_diag_progress(NES_DIAG_BLOCKED,0,0);return false;}')
 body=replace(body,' if(usb_irq_enabled)NVIC_EnableIRQ(OTG_FS_IRQn);',' nes_diag_leave();\n if(usb_irq_enabled)NVIC_EnableIRQ(OTG_FS_IRQn);')
 prefix=replace(prefix,' if(!(address&255u)) {',' if(!(address&255u)) {\n  nes_diag_progress(NES_DIAG_CHECK,address,c->total);')
 return prefix+body

def sd_source(s):
 s=replace(s,'#include "config.h"','#include "config.h"\n#include "nes_diag_runtime.h"\nstatic bool nes_diag_sd_fault;\nstatic void nes_diag_sd_error(enum nes_diag_error);')
 s=replace(s,'static inline void wait_busy(void) {','static inline void wait_busy(void) {\n  struct nes_diag_wait wait=nes_diag_wait_start(100,2000000u);')
 s=replace(s,'  while(!(BITBAND(SD_DAT0REG->GPIO_I, SD_DAT0BIT))) {',
  '  while(!(BITBAND(SD_DAT0REG->GPIO_I, SD_DAT0BIT))) {\n    if(nes_diag_active()&&!nes_diag_wait_step(&wait)){nes_diag_sd_error(NES_DIAG_SD_BUSY);return;}')
 s=replace(s,'  static int state=CMD_RSP;','  static int state=CMD_RSP;\n  if(nes_diag_active()){if(nes_diag_sd_fault)return 0;state=CMD_RSP;}')
 # Only the fast-command timeout; leave slow/init legacy commands intact.
 pos=s.index('int send_command_fast(');end=s.index('int cmd_fast(',pos)
 head=s[:pos];body=s[pos:end];tail=s[end:]
 body=replace(body,'      return 0; /* no response within timeout */','      if(nes_diag_active())nes_diag_sd_error(NES_DIAG_SD_RESPONSE);\n      return 0; /* no response within timeout */')
 body=replace(body,'      if(!timeout) printf("timed out!\\n");','      if(!timeout) {\n        if(nes_diag_active()){state=CMD_RSP;nes_diag_sd_error(NES_DIAG_SD_DATA);return 0;}\n        printf("timed out!\\n");\n      }')
 body=replace(body,'    if(dat) {\n#ifdef CONFIG_SD_DATACRC','    if(dat) {\n     if(nes_diag_active()){\n      int bad=get_and_check_datacrc(buf-512);\n      if(bad){state=CMD_RSP;nes_diag_sd_error(NES_DIAG_SD_CRC);return CRC_ERROR;}\n     } else {\n#ifdef CONFIG_SD_DATACRC')
 body=replace(body,'#endif\n    }\n\n    if(waitbusy)','#endif\n     }\n    }\n\n    if(waitbusy)')
 body=replace(body,'      wait_busy();','      wait_busy();\n      if(nes_diag_active()&&nes_diag_sd_fault){state=CMD_RSP;return 0;}')
 s=head+body+tail
 s=replace(s,'DRESULT sdn_read(BYTE drv, BYTE *buffer, DWORD sector, UINT count) {',
  (FW/'nes_diag_sd.inc').read_text()+'\nDRESULT sdn_read(BYTE drv, BYTE *buffer, DWORD sector, UINT count) {\n  if(nes_diag_active())return nes_diag_sd_read(drv,buffer,sector,count);')
 s=replace(s,'DSTATUS sdn_initialize(BYTE drv) {','DSTATUS sdn_initialize(BYTE drv) {\n  if(nes_diag_active()){nes_diag_sd_error(NES_DIAG_SD_STATE);return STA_NOINIT;}')
 s=replace(s,'    if (disk_state == DISK_CHANGED) {','    if (disk_state == DISK_CHANGED || (nes_diag_active()&&(disk_state!=DISK_OK||nes_diag_sd_fault))) {')
 s=replace(s,'DRESULT sdn_write(BYTE drv, const BYTE *buffer, DWORD sector, UINT count) {',
  'DRESULT sdn_write(BYTE drv, const BYTE *buffer, DWORD sector, UINT count) {\n  if(nes_diag_active()){nes_diag_sd_error(NES_DIAG_SD_STATE);return RES_WRPRT;}')
 s=replace(s,'DRESULT sdn_ioctl(BYTE drv, BYTE cmd, void *buffer) {',
  'DRESULT sdn_ioctl(BYTE drv, BYTE cmd, void *buffer) {\n  if(nes_diag_active())return drv>=MAX_CARDS?RES_PARERR:cmd!=CTRL_SYNC?RES_PARERR:nes_diag_sd_fault||during_blocktrans!=TRANS_NONE?RES_ERROR:RES_OK;')
 return s

def materialize(out):
 materialize062(out)
 (out/'nes_h1_stm32.c').write_text(source(),encoding='utf-8',newline='\n')
 for n in ['nes_diag_runtime.c','nes_diag_runtime.h','nes_diag_platform.c']:shutil.copy2(FW/n,out/n)
 menu=out/'nes_menu_diagnostic.c';s=menu.read_text().replace('062','064')
 s=replace(s,'#include "nes_menu_diagnostic.h"','#include "nes_menu_diagnostic.h"\n#include "nes_diag_runtime.h"')
 s=replace(s,' printf("%s",text);',' printf("%s",text);\n const struct nes_diag_report *r=nes_diag_status();\n printf("NES064 final phase=%u error=%u progress=%lu/%lu\\n",(unsigned)r->phase,(unsigned)r->error,(unsigned long)r->completed,(unsigned long)r->total);')
 menu.write_text(s,encoding='utf-8',newline='\n')

def uart_source(s):
 s=replace(s,'#include "config.h"','#include "config.h"\n#include "nes_diag_runtime.h"\nvolatile uint32_t nes_diag_uart_dropped;')
 return replace(s,'  while(!(BITBAND(UART_REGS->SR, USART_SR_TXE_Pos)));','  struct nes_diag_wait wait=nes_diag_wait_start(1,100000u);\n  while(!(BITBAND(UART_REGS->SR, USART_SR_TXE_Pos)))\n    if(nes_diag_active()&&!nes_diag_wait_step(&wait)){nes_diag_uart_dropped++;return;}',2)

def prepare(baseline,out):
 old=json.loads((baseline/'menu-diagnostic-preparation.json').read_text())
 assert old['candidate']=='NES-MENU-DIAGNOSTIC-062'
 for n,h in old['files'].items():assert sha(baseline/'src'/n)==h,n
 for n,h in PINNED.items():assert sha(baseline/'src'/n)==h,n
 assert (baseline/'src/nes_h1_stm32.c').read_text()==source062()
 assert not out.exists()
 shutil.copytree(baseline,out,ignore=shutil.ignore_patterns('obj*','.dep*','*.elf','*.stm','*.map','*.lst'))
 src=out/'src';materialize(src)
 f=src/'fpga.c';f.write_text(f.read_text()+'\n'+(FW/'nes_diag_fpga.inc').read_text(),encoding='utf-8',newline='\n')
 f=src/'stm32f4xx/sdnative.c';f.write_text(sd_source(f.read_text()),encoding='utf-8',newline='\n')
 f=src/'stm32f4xx/led.c';s=f.read_text();s=replace(s,'#include "config.h"','#include "config.h"\n#include "nes_diag_runtime.h"');s=replace(s,'void led_error() {','void led_error() {\n  if(nes_diag_active()){nes_diag_led_tick();return;}');f.write_text(s,encoding='utf-8',newline='\n')
 f=src/'stm32f4xx/uart.c';f.write_text(uart_source(f.read_text()),encoding='utf-8',newline='\n')
 f=src/'main.c';s=f.read_text();s=replace(s,'#include "nes_menu_diagnostic.h"','#include "nes_menu_diagnostic.h"\n#include "nes_diag_runtime.h"')
 s=replace(s,'              led_panic(LED_PANIC_FPGA_NOCONF);\n              for(;;); /* RESET remains held on unsafe recovery. */','              nes_diag_blocked();',3)
 s=replace(s,'      led_panic(LED_PANIC_FPGA_NOCONF);\n      for(;;); /* Do not release RESET after failed menu preparation. */','      nes_diag_blocked();')
 f.write_text(s,encoding='utf-8',newline='\n')
 f=src/'Makefile';s=replace(f.read_text(),'nes_menu_diagnostic.c','nes_menu_diagnostic.c nes_diag_runtime.c nes_diag_platform.c');f.write_text(s,encoding='utf-8',newline='\n')
 names=list(old['files'])+['fpga.c','stm32f4xx/sdnative.c','stm32f4xx/led.c','stm32f4xx/uart.c','nes_diag_runtime.c','nes_diag_runtime.h','nes_diag_platform.c']
 (out/'diag-recovery-preparation.json').write_text(json.dumps(dict(candidate='NES-DIAG-RECOVERY-064',installable=False,
  baseline_preparation_sha256=sha(baseline/'menu-diagnostic-preparation.json'),files={n:sha(src/n) for n in names}),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.baseline,a.out)
 print('Prepared064 diagnostic-only lower read/configuration; compile-only, not installable')
