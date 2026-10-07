# SPDX-License-Identifier: MIT
"""065 menu recovery overlay; immutable064 inputs remain unchanged."""
from pathlib import Path
import argparse,json,shutil
from nes_diag_recovery import prepare as prepare064,materialize as materialize064
from nes_menu_diagnostic import replace
from nes_mcu_loader import FW,sha

def materialize(out):
 materialize064(out)
 for n in ['nes_menu_return.h','nes_menu_return.c']:shutil.copy2(FW/n,out/n)
 f=out/'nes_diag_runtime.h';s=replace(f.read_text(),'NES_DIAG_FPGA_CLOSE};','NES_DIAG_FPGA_CLOSE,NES_DIAG_SPI,NES_DIAG_TIMER,NES_DIAG_MENU};');f.write_text(s,encoding='utf-8',newline='\n')
 f=out/'nes_h1_stm32.c';s=replace(f.read_text(),'#include "nes_diag_runtime.h"','#include "nes_diag_runtime.h"\n#include "nes_menu_return.h"')
 s=replace(s,' nes_diag_leave();\n if(usb_irq_enabled)NVIC_EnableIRQ(OTG_FS_IRQn);',' if(!nes_menu_diagnostic_pending()){\n  nes_diag_leave();\n  if(usb_irq_enabled)NVIC_EnableIRQ(OTG_FS_IRQn);\n }')
 f.write_text(s,encoding='utf-8',newline='\n')
 f=out/'nes_menu_diagnostic.c';s=f.read_text().replace('064','065')
 s=replace(s,'#include "nes_diag_runtime.h"','#include "nes_diag_runtime.h"\n#include "nes_menu_return.h"')
 s=s.replace('#include "nes_menu_return.h"','#include "nes_menu_return.h"\n#include "snes.h"')
 s=replace(s,'static bool pending, safe_to_reload, prepared;','static bool pending, safe_to_reload, prepared, saved_irq;\nbool nes_menu_diagnostic_pending(void){return pending;}')
 s=replace(s,' geometry=selected;pending=true;prepared=false;safe_to_reload=false;',''' saved_irq=NVIC_GetEnableIRQ(OTG_FS_IRQn)!=0;NVIC_DisableIRQ(OTG_FS_IRQn);snes_reset(1);
 nes_return_reset();nes_diag_sd_reset();nes_diag_begin();
 geometry=selected;pending=true;prepared=false;safe_to_reload=false;''')
 s=replace(s,' if(!safe_to_reload||!menu_ok)return false;\n prepared=true;save_report("PREPARED_RESET_HELD",true);return true;',''' if(!safe_to_reload||!menu_ok||nes_return_failed())return false;
 nes_return_log_allow(true);save_report("PREPARED_RESET_HELD",true);nes_return_log_allow(false);
 if(nes_return_failed())return false;
 prepared=true;return true;''')
 s=replace(s,' if(pending&&safe_to_reload&&prepared){save_report("RELEASE_BOUNDARY_REACHED",true);pending=false;}',''' if(pending&&safe_to_reload&&prepared){
  save_report("RETURN_READY_RESET_RELEASED",false);pending=false;nes_diag_leave();
  if(saved_irq)NVIC_EnableIRQ(OTG_FS_IRQn);
 }''')
 f.write_text(s,encoding='utf-8',newline='\n')
 f=out/'nes_diag_platform.c';f.write_text(f.read_text().replace('NES064','NES065'),encoding='utf-8',newline='\n')

def spi_source(s):
 s=replace(s,'#include "config.h"','#include "config.h"\n#include "nes_menu_return.h"')
 # Helpers before public byte/block functions. Inactive legacy bodies intact.
 s=replace(s,'void spi_tx_sync() {',(FW/'nes_return_spi.inc').read_text()+'\nvoid spi_tx_sync() {\n  if(nes_diag_active()){(void)nes_return_spi_wait(SPI_SR_BSY_Pos,false);return;}')
 s=replace(s,'void spi_tx_byte(uint8_t data) {','void spi_tx_byte(uint8_t data) {\n  if(nes_diag_active()){if(nes_return_spi_wait(SPI_SR_TXE_Pos,true))SPI1->DR=data;return;}')
 for old,new in [('uint8_t spi_txrx_byte(uint8_t data) {','uint8_t spi_txrx_byte(uint8_t data) {\n  if(nes_diag_active())return nes_return_spi_exchange(data);'),('uint8_t spi_rx_byte() {','uint8_t spi_rx_byte() {\n  if(nes_diag_active())return nes_return_spi_exchange(0xff);')]:s=replace(s,old,new)
 s=replace(s,'void spi_tx_block(const void *ptr, unsigned int length) {','void spi_tx_block(const void *ptr, unsigned int length) {\n  if(nes_diag_active()){const uint8_t *p=ptr;while(length--&&!nes_return_failed())spi_tx_byte(*p++);return;}')
 s=replace(s,'void spi_rx_block(void *ptr, unsigned int length) {','void spi_rx_block(void *ptr, unsigned int length) {\n  if(nes_diag_active()){uint8_t *p=ptr;while(length--&&!nes_return_failed())*p++=spi_rx_byte();return;}')
 return s

def timer_source(s):
 s=replace(s,'#include "config.h"','#include "config.h"\n#include "nes_menu_return.h"')
 for kind in ['us','ms']:s=replace(s,'void delay_'+kind+'(unsigned int time) {','void delay_'+kind+'(unsigned int time) {\n  if(nes_diag_active()){(void)nes_return_delay(time,'+('true' if kind=='ms' else 'false')+');return;}')
 return s+'\n'+(FW/'nes_return_timer.inc').read_text()

def sd_source(s):
 s=replace(s,'  if(nes_diag_active())return nes_diag_sd_read(drv,buffer,sector,count);','  if(nes_diag_active()&&nes_return_failed())return RES_NOTRDY;\n  if(nes_diag_active())return nes_diag_sd_read(drv,buffer,sector,count);')
 s=replace(s,'#include "nes_diag_runtime.h"','#include "nes_diag_runtime.h"\n#include "nes_menu_return.h"')
 s=replace(s,'    while(1);\n  }\n  if(dat0 & 8)', '    if(nes_diag_active()){nes_diag_sd_error(NES_DIAG_SD_CRC);return;}\n    while(1);\n  }\n  if(dat0 & 8)')
 s=replace(s,'  if(dat0 & 8) {','  if(dat0 & 8) {\n    if(nes_diag_active()){nes_diag_sd_error(NES_DIAG_SD_RESPONSE);return;}')
 s=replace(s,'DRESULT sdn_write(BYTE drv, const BYTE *buffer, DWORD sector, UINT count) {\n  if(nes_diag_active()){nes_diag_sd_error(NES_DIAG_SD_STATE);return RES_WRPRT;}',
  (FW/'nes_return_sd_write.inc').read_text()+'\nDRESULT sdn_write(BYTE drv, const BYTE *buffer, DWORD sector, UINT count) {\n  if(nes_diag_active())return nes_return_sd_write(drv,buffer,sector,count);')
 return s

def memory_source(s):
 s=replace(s,'#include "config.h"','#include "config.h"\n#include "nes_menu_return.h"')
 s=replace(s,'uint32_t load_rom(uint8_t* filename, uint32_t base_addr, uint8_t flags) {','''uint32_t load_rom(uint8_t* filename, uint32_t base_addr, uint8_t flags) {
  if(nes_diag_active()&&(!nes_menu_diagnostic_pending()||strcmp((const char *)filename,MENU_FILENAME)||flags)) {nes_return_fail(NES_DIAG_MENU);return 0;}''')
 s=replace(s,'  uint8_t is_menu = (filename == (uint8_t*)MENU_FILENAME);','  uint8_t is_menu = nes_diag_active() || (filename == (uint8_t*)MENU_FILENAME);')
 s=replace(s,"  filesize = file_handle.fsize; // won't be correct for combo roms", """  filesize = file_handle.fsize; // won't be correct for combo roms
  if(nes_diag_active()&&(!filesize||filesize>0x400200u)){file_close();nes_return_fail(NES_DIAG_MENU);return 0;}""")
 s=replace(s,'  if(msu1_check(filename)) {','  if(!nes_diag_active()&&msu1_check(filename)) {')
 s=replace(s,'  smc_id(&romprops, file_offset);\n  file_close();','''  smc_id(&romprops, file_offset);
  file_close();
  if(nes_diag_active()&&(nes_return_failed()||!romprops.romsize_bytes||romprops.romsize_bytes>0x400000u||romprops.offset>=filesize||romprops.load_address||romprops.fpga_conf||romprops.header.carttype>2||romprops.mapper_id>1||romprops.has_dspx||romprops.has_combo||sgb_romprops.has_sgb||sgb_romprops.has_egbc)){nes_return_fail(NES_DIAG_MENU);return 0;}''')
 start=s.index('  {\n    set_mcu_addr(base_addr + romprops.load_address);',s.index('uint32_t load_rom('));end=s.index("  uart_putc('\\n');",start)
 original=s[start:end]
 s=s[:start]+'''  if(nes_diag_active()) {
    total_bytes_read=nes_return_copy_menu((const char *)filename,base_addr+romprops.load_address,romprops.offset);
    if(!total_bytes_read)return 0;
  } else
'''+original+s[end:]
 return s

def main_source(s):
 s=replace(s,'#include "nes_diag_runtime.h"','#include "nes_diag_runtime.h"\n#include "nes_menu_return.h"')
 s=replace(s,'    snes_boot_configured = 0;','''    snes_boot_configured = 0;
    if(nes_menu_diagnostic_pending()) {
      nes_return_io_begin();
      if(get_cic_state()==CIC_FAIL||nes_return_failed())nes_diag_blocked();
      goto nes_return_menu_ready;
    }''')
 s=replace(s,'    led_pwm();\n    rdyled(1);','nes_return_menu_ready:\n    if(!nes_menu_diagnostic_pending())led_pwm();\n    rdyled(1);')
 s=replace(s,'    if(fpga_config != FPGA_BASE) fpga_pgm((uint8_t*)FPGA_BASE);','    if(!nes_menu_diagnostic_pending()&&fpga_config != FPGA_BASE) fpga_pgm((uint8_t*)FPGA_BASE);')
 # Lists are auxiliary state already in MCU; avoid unchecked path strings and
 # parsing/files during this constrained re-entry. Empty lists remain usable.
 for field,path,address in [('num_recent_games','LAST_FILE','SRAM_LASTGAME_ADDR'),('num_favorite_games','FAVORITES_FILE','SRAM_FAVORITEGAMES_ADDR')]:
  old=f'\n    STM.{field} = cfg_dump_listed_games_for_snes({path}, {address});'
  s=replace(s,old,f'\n    STM.{field} = nes_menu_diagnostic_pending()?0:cfg_dump_listed_games_for_snes({path}, {address});')
 s=replace(s,'    cfg_load_to_menu();\n    cfg_save();','    cfg_load_to_menu();\n    if(!nes_menu_diagnostic_pending())cfg_save();')
 s=replace(s,'    nes_menu_diagnostic_released();\n','')
 s=replace(s,'    while(!sram_reliable()) cli_entrycheck();',"""    if(nes_menu_diagnostic_pending()) {
      if(nes_return_failed()||get_cic_state()==CIC_FAIL||!sram_reliable()||nes_return_failed()) {
        snes_reset(1);nes_diag_blocked();
      }
      nes_menu_diagnostic_released();
    } else while(!sram_reliable()) cli_entrycheck();""")
 return s

def fatfs_source(s):
 s=replace(s,'#include "ff.h"','#include "ff.h"\n#include "nes_menu_return.h"')
 from nes_diag_recovery_checks import function
 for name,value in [('move_window','FR_DISK_ERR'),('get_fat','0xFFFFFFFF')]:
  old=function(s,name);new=old.replace('{','{\n if(nes_diag_active()&&!nes_return_io_step())return '+value+';',1)
  s=replace(s,old,new)
 return s

def prepare(baseline,out):
 pins={'ff.c':'adcd3facbc7c33399b68baaf976aceb39c1b2bb8402bf034aff55bbe86748bb4','stm32f4xx/spi.c':'fb0b9f290a17febc7f22db6c2d5f05431825369fb2e476fbfcbb88e028dfed88','memory.c':'f3fc010f3b94c9099c0d80c347e5e362e73ec0aee58298bad787daffd710b106','fpga_spi.h':'fcb200291453de294b7ef5b880f9e0ba104db45ceb7f7c360b652e9bf740a3c5'}
 for n,h in pins.items():assert sha(baseline/'src'/n)==h,n
 prepare064(baseline,out);src=out/'src';materialize(src)
 for n,fn in [('stm32f4xx/spi.c',spi_source),('stm32f4xx/timer.c',timer_source),('stm32f4xx/sdnative.c',sd_source),('memory.c',memory_source),('main.c',main_source),('ff.c',fatfs_source)]:
  f=src/n;f.write_text(fn(f.read_text()),encoding='utf-8',newline='\n')
 f=src/'fpga_spi.h';s=f.read_text();line=next(l for l in s.splitlines() if l.startswith('#define FPGA_WAIT_RDY()'));legacy=line.split('    ',1)[1]
 s=replace(s,line,'#include "nes_menu_return.h"\n#define FPGA_WAIT_RDY() do {if(nes_diag_active())(void)nes_return_spi_ready();else '+legacy+';}while(0)');f.write_text(s,encoding='utf-8',newline='\n')
 f=src/'Makefile';s=replace(f.read_text(),'nes_diag_platform.c','nes_diag_platform.c nes_menu_return.c');f.write_text(s,encoding='utf-8',newline='\n')
 old=json.loads((out/'diag-recovery-preparation.json').read_text());names=list(old['files'])+['nes_menu_return.h','nes_menu_return.c','stm32f4xx/spi.c','stm32f4xx/timer.c','memory.c','fpga_spi.h','ff.c']
 (out/'menu-return-preparation.json').write_text(json.dumps(dict(candidate='NES-MENU-RETURN-065',installable=False,files={n:sha(src/n) for n in names}),indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.baseline,a.out);print('Prepared065 menu recovery; compile-only')
