/* SPDX-License-Identifier: GPL-2.0-only */
#include <string.h>
#include "config.h"
#include "snes.h"
#include "fileops.h"
#include "nes_menu_return.h"
#include "nes_sd_inventory.h"
#include "nes_sd_fault074.h"
#include "nes_report_boot080.h"
extern bool sdn_report_initialize081(void);
extern int sd_offload,ff_sd_offload,during_blocktrans;
extern bool report_space084(unsigned bytes);
static char text[3072];

/* No SD access, file permission, or deadline restart. The successful SRAM
 * compare precedes RESET release. A timed rendering opportunity is not ACK. */
static bool marker084(const char *label) {
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

bool report_session084(void) {
 /* MCU clock/GPIO/timer/CIC setup remains a precondition. Embedded mini
  * and boot ROM require no SD read and are prepared before card commands. */
 snes_reset(1);NVIC_DisableIRQ(OTG_FS_IRQn);
 if(nes_diag_active()||nes_return_failed()){nes_return_fail(NES_DIAG_MENU);return false;}
 sd_offload=ff_sd_offload=0;nes_return_reset();nes_diag_sd_reset();
 sdinv_fault_stage(1);nes_diag_begin();nes_return_io_begin();
 if(!report_boot080()||!report_line080(5,"SDREPORT084 STORAGE TEST")||
    !report_line080(16,"POWER OFF / RESTORE 044")||
    !marker084("STEP 1A INIT SD"))return false;
 if(!sdn_report_initialize081()||!marker084("STEP 1B MOUNT FAT"))return false;
 file_init();
 if(!nes_return_io_step())return false;
 if(file_res!=FR_OK){nes_return_fail(NES_DIAG_SD_STATE);return false;}
 if(!marker084("STEP 1C FIND SPACE")||!report_space084(sizeof(text)))return false;
 for(unsigned i=0;i<sizeof(text);i++)text[i]=(i%64==63)?'\n':(char)('A'+i%26);
 const char header[]="SDREPORT084-NATIVE077\nSTORAGE PAYLOAD; FILE ALONE DOES NOT PROVE SUCCESS\n";
 memcpy(text,header,sizeof(header)-1);
 char path[16]={0};int result=sdinv_write_report(text,sizeof(text),path,sizeof(path));
 if(result==8||nes_return_failed())return false;
 sdinv_fault_stage(9);
 char code[]="Save code: 0";code[11]=(char)('0'+result);
 if(!report_line080(8,result?"TXT SAVE FAILED":"TXT SAVED + READBACK OK")||
    !report_line080(11,path)||!report_line080(13,code)||
    !nes_return_io_step()||!get_snes_reset())return false;
 snes_reset(0);return true;
}
void sdreport_run084(void) __attribute__((noreturn));
void sdreport_run084(void) {
 if(!report_session084())nes_diag_blocked();
 for(;;)__NOP();
}
