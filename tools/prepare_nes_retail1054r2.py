"""Rebuild the release ARM from the paired 1054 sources. FPGA and debug stay paired."""
import shutil
from prepare_nes_pair1054 import ROOT, WORK
from prepare_nes_kirby1023 import edit

OUT = WORK.parent / 'nes-pair1054r2'

def prepare():
    link = OUT / 'release/link'
    shutil.copytree(WORK / 'release/link', link)
    src = link / 'src'
    edit(src, 'nes_menu_diagnostic.c',
         ('static void save_report', '''#include "timer.h"
bool nes_menu_blank1054;
static bool menu_reply1054(uint8_t command,uint8_t reply) {
 tick_t start=getticks();
 snes_set_snes_cmd(command);
 do {
  if(snes_get_mcu_cmd()==reply)return true;
 }while((tick_t)(getticks()-start)<MS_TO_TICKS(2000));
 return false;
}
static void save_report'''),
         ('NVIC_DisableIRQ(OTG_FS_IRQn);snes_reset(1);',
          '''NVIC_DisableIRQ(OTG_FS_IRQn);
 nes_menu_blank1054=menu_reply1054(0x55,SNES_CMD_FPGA_RECONF) && menu_reply1054(0x77,SNES_CMD_RESET);
 snes_reset(1);delay_ms(SNES_RESET_PULSELEN_MS);'''))
    edit(src,'nes_h1_stm32.c',
         ('bool staged=retail_stage1054(path,r);',
          'extern bool nes_menu_blank1054;\n bool staged=nes_menu_blank1054 && retail_stage1054(path,r);'),
         ('||(staged&&changed_fpga&&', '||(begin_sent&&changed_fpga&&'))
    inc='nes_retail_preload1054.inc'
    edit(src,inc,
         ('static __attribute__((noinline,noclone)) bool retail_stage1054', """/* RDY is also high before the mini has received the byte. Wait for
 * completed wire transfer before sampling the PSRAM request handshake. */
static __attribute__((noinline,noclone)) bool retail_write_page1054(uint8_t *page,uint32_t address,unsigned count) {
 set_mcu_addr(address);
 FPGA_SELECT(); FPGA_TX_BYTE(0x98);
 for(unsigned i=0;i<count;i++){
  (void)FPGA_TXRX_BYTE(page[i]);
  if(!nes_return_spi_ready()){FPGA_DESELECT();return false;}
 }
 FPGA_DESELECT();
 return !nes_return_failed();
}
static __attribute__((noinline,noclone)) bool retail_stage1054"""),
         ('sram_writeblock(data,dest,sizeof block);',
          """if(!retail_write_page1054(data,dest,sizeof block)){r->result=NES_MCU_LOAD_SPI;goto closed;}"""),
         ('if(shown!=pct)', 'if(pct<20 && shown!=pct)'),
         (' snes_reset(1);\n snes_boot_configured=0;\n r->file_result=f_close(&file);',
          """ if(nes_return_failed()){snes_reset(1);snes_boot_configured=0;return false;}
 r->file_result=f_close(&file);
 if(!nes_return_failed() && snes_boot_configured){
  if(ok && r->file_result==FR_OK){
   snes_bootprint_center(12,"100%%");
   snes_bootprint_center(14,"Starting NES");
  }else snes_bootprint_center(14,"ROM read failed");
  delay_ms(ok?100:1000);
 }
 snes_reset(1);
 delay_ms(SNES_RESET_PULSELEN_MS);
 snes_boot_configured=0;"""),
         ('||!slow_begin()||!identify136(io,candidate)', '||!slow_begin()'),
         (' *begun=true;', """ /* Only read identity while the observer clock and reset synchronize.
  * Never repeat BEGIN, END or START on an uncertain acknowledgement. */
 for(unsigned poll=0;;poll++){
  if(identify136(io,candidate))break;
  if(nes_return_failed() || poll==19){r->result=NES_MCU_LOAD_ID;return false;}
  delay_ms(1);
 }
 *begun=true;"""))

if __name__=='__main__':
    prepare()
