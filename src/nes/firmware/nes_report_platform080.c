/* SPDX-License-Identifier: GPL-2.0-only */
#include <string.h>
#include "config.h"
#include "snes.h"
#include "fileops.h"
#include "nes_menu_return.h"
#include "nes_sd_inventory.h"
#include "nes_sd_fault074.h"
#include "nes_report_boot080.h"
extern int sd_offload,ff_sd_offload;
static char text[3072];
bool report_session080(void) {
 /* main's card mount/CIC initialization still precedes this bounded scope.
  * Never activate the legacy sdn_initialize: active077 intentionally rejects it. */
 snes_reset(1);NVIC_DisableIRQ(OTG_FS_IRQn);
 if(nes_diag_active()||nes_return_failed()){nes_return_fail(NES_DIAG_MENU);return false;}
 sd_offload=ff_sd_offload=0;nes_return_reset();nes_diag_sd_reset();
 sdinv_fault_stage(1);nes_diag_begin();nes_return_io_begin();
 if(file_res!=FR_OK){nes_return_fail(NES_DIAG_SD_STATE);return false;}
 if(!report_boot080()||!report_line080(5,"SDREPORT080 STORAGE TEST")||
    !report_line080(16,"POWER OFF THEN RESTORE NORMAL"))return false;
 for(unsigned i=0;i<sizeof(text);i++)text[i]=(i%64==63)?'\n':(char)('A'+i%26);
 const char header[]="SDREPORT080-NATIVE077\nSTORAGE PAYLOAD; FILE ALONE DOES NOT PROVE SUCCESS\n";
 memcpy(text,header,sizeof(header)-1);
 char path[16]={0};int result=sdinv_write_report(text,sizeof(text),path,sizeof(path));
 if(result==8||nes_return_failed())return false;
 sdinv_fault_stage(9);
 char code[]="Save code: 0";code[11]=(char)('0'+result);
 if(!report_line080(8,result?"TXT SAVE FAILED":"TXT SAVED + READBACK OK")||
    !report_line080(11,path)||!report_line080(13,code)||
    !nes_return_io_step()||!get_snes_reset())return false;
 snes_reset(0);
 return true; /* active/USB exclusion persists, with no further peripheral IO */
}
void sdreport_run080(void) __attribute__((noreturn));
void sdreport_run080(void) {
 if(!report_session080())nes_diag_blocked();
 for(;;)__NOP();
}
