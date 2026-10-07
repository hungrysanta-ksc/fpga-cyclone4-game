/* SPDX-License-Identifier: GPL-2.0-only */
#include <string.h>
#include "config.h"
#include "snes.h"
#include "nes_menu_return.h"
#include "nes_sd_inventory.h"
#include "nes_sd_inventory_log073.h"
#include "nes_sd_fault074.h"
extern int sd_offload,ff_sd_offload;
static char text[3072];
void sdreport_run079(void) __attribute__((noreturn));
void sdreport_run079(void) {
 /* Compile-only candidate: legacy mini bootstrap and file_init remain outside
  * the bounded report scope. This must not be packaged as install-approved. */
 snes_bootclear();snes_bootprint_version();
 snes_bootprint_center(5,"SDREPORT079 STORAGE TEST");
 snes_bootprint_center(16,"POWER OFF THEN RESTORE NORMAL");
 snes_reset(1);NVIC_DisableIRQ(OTG_FS_IRQn);
 sd_offload=ff_sd_offload=0;nes_return_reset();nes_diag_sd_reset();
 sdinv_fault_stage(1);nes_diag_begin();nes_return_io_begin();
 /* Deterministic storage payload, not fabricated hardware inventory. The
  * existence of this file does not prove sync/close/readback completion. */
 for(unsigned i=0;i<sizeof(text);i++)text[i]=(i%64==63)?'\n':(char)('A'+i%26);
 const char header[]="SDREPORT079-NATIVE077\nSTORAGE PAYLOAD; FILE ALONE DOES NOT PROVE SUCCESS\n";
 memcpy(text,header,sizeof(header)-1);
 char path[16]={0};
 int result=sdinv_write_report(text,sizeof(text),path,sizeof(path));
 if(result==8||nes_return_failed())nes_diag_blocked();
 sdinv_fault_stage(9);
 snes_bootprint_center(8,result?"TXT SAVE FAILED":"TXT SAVED + READBACK OK");
 snes_bootprint_center(11,"%s",path);
 snes_bootprint_center(13,"Save code: %d",result);
 if(nes_return_failed())nes_diag_blocked();
 /* Active protection and USB exclusion persist. No menu or additional SD IO. */
 snes_reset(0);
 for(;;)__NOP();
}
