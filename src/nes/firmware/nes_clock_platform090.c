/* SPDX-License-Identifier: GPL-2.0-only */
#include "config.h"
#include "snes.h"
#include "fileops.h"
#include "nes_menu_return.h"
#include "nes_sd_inventory.h"
#include "nes_sd_fault074.h"
#include "nes_report_boot080.h"
#include "nes_clock_config089.h"
#include "nes_clock_report090.h"
#include "clock089_payload.h"
extern bool sdn_report_initialize081(void);
extern int sd_offload,ff_sd_offload,during_blocktrans;
extern bool report_space084(unsigned);
static char text090[3072];
static struct clock_report088 report090;
static bool marker090(const char *label) {
 if(nes_return_failed())return false;
 if(!nes_diag_active()||nes_return_log_allowed()||sd_offload||ff_sd_offload||
    during_blocktrans||!get_snes_reset()||
    (NVIC->ISER[OTG_FS_IRQn>>5]&(1u<<(OTG_FS_IRQn&31))))goto fail;
 if(!report_line080(8,label)||!nes_return_io_step())goto fail;
 snes_reset(0);
 if(!nes_return_delay(1000,true)||get_snes_reset())goto fail;
 snes_reset(1);
 if(!get_snes_reset()||!nes_return_io_step())goto fail;
 return true;
fail:
 snes_reset(1);nes_return_fail(NES_DIAG_MENU);return false;
}
static bool title090(void) {
 return report_line080(5,"CLOCKREPORT090 CF87")&&report_line080(16,"POWER OFF / RESTORE 044");
}
bool report_session090(void) {
 snes_reset(1);NVIC_DisableIRQ(OTG_FS_IRQn);
 if(nes_diag_active()||nes_return_failed()){nes_return_fail(NES_DIAG_MENU);return false;}
 sd_offload=ff_sd_offload=0;nes_return_reset();nes_diag_sd_reset();
 sdinv_fault_stage(1);nes_diag_begin();nes_return_io_begin();
 if(!report_boot080()||!title090()||!marker090("STEP 1A OBSERVE CLOCK"))return false;
 const struct clock_image089 image={clock089_rle,sizeof(clock089_rle),CLOCK089_RAW_SIZE,CLOCK089_CRC};
 if(!nes_clock_config089(&image)||!nes_clock_collect088(&report090)||nes_return_failed())return false;
 unsigned length=clock_text090(text090,sizeof(text090),&report090);
 if(!length){nes_return_fail(NES_DIAG_MENU);return false;}
 if(!report_boot080()||!title090()||!report_line080(10,clock_label090(report090.result))||
    !marker090("STEP 1B INIT SD"))return false;
 if(!sdn_report_initialize081()||!marker090("STEP 1C MOUNT FAT"))return false;
 file_init();
 if(!nes_return_io_step())return false;
 if(file_res!=FR_OK){nes_return_fail(NES_DIAG_SD_STATE);return false;}
 if(!marker090("STEP 1D FIND SPACE")||!report_space084(length))return false;
 char path[16]={0};int result=sdinv_write_report(text090,length,path,sizeof(path));
 if(result==8||nes_return_failed())return false;
 sdinv_fault_stage(9);char code[]="Save code: 0";code[11]=(char)('0'+result);
 if(!report_line080(8,result?"TXT SAVE FAILED":"TXT SAVED + READBACK OK")||
    !report_line080(11,path)||!report_line080(13,code)||
    !nes_return_io_step()||!get_snes_reset())return false;
 snes_reset(0);return true;
}
void sdreport_run090(void) __attribute__((noreturn));
void sdreport_run090(void) {
 if(!report_session090())nes_diag_blocked();
 for(;;)__NOP();
}
