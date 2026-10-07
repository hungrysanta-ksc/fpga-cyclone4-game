/* SPDX-License-Identifier: GPL-2.0-only */
#include <string.h>
#include "config.h"
#include "ff.h"
#include "snes.h"
#include "diskio.h"
#include "nes_diag_runtime.h"
#include "nes_menu_return.h"
#include "nes_sd_inventory.h"
extern int sd_offload,ff_sd_offload;
static FIL input;
static struct sdinv_report report;
static char text[6144];
static int opened(void *ctx,const char *path,uint32_t *size){
 (void)ctx;FRESULT r=f_open(&input,path,FA_READ);
 if(r==FR_OK){*size=f_size(&input);return 0;}
 return r==FR_NO_FILE||r==FR_NO_PATH?1:2;
}
static int read_input(void *ctx,uint8_t *p,unsigned n,unsigned *got){(void)ctx;UINT amount=0;FRESULT r=f_read(&input,p,n,&amount);*got=amount;return r!=FR_OK;}
static int seek_input(void *ctx,uint32_t at){(void)ctx;return f_lseek(&input,at)!=FR_OK||input.fptr!=at;}
static int close_input(void *ctx){(void)ctx;return f_close(&input)!=FR_OK;}
static int step(void *ctx){(void)ctx;return nes_return_io_step();}
static int blocked(void *ctx){(void)ctx;return nes_return_failed();}
void sdinv_run(void){
 /* Existing embedded-mini boot screen only. This precedes the bounded SD scope.
  * Its legacy boot programming waits have not acquired a new termination proof. */
 snes_bootclear();snes_bootprint_version();
 snes_bootprint_center(5,"SDINFO072 READ ONLY INPUTS");
 snes_bootprint_center(8,"READING SD - WAIT FOR TXT");
 snes_reset(1);NVIC_DisableIRQ(OTG_FS_IRQn);
 sd_offload=ff_sd_offload=0;nes_return_reset();nes_diag_sd_reset();
 nes_diag_begin();nes_return_io_begin();
 const struct sdinv_io io={0,opened,read_input,seek_input,close_input,step,blocked};
 int collected=sdinv_collect(&io,&report);
 if(!collected||nes_return_failed())nes_diag_blocked();
 int n=sdinv_format(&report,text,sizeof(text));char path[16]={0};
 int result=n<0?1:sdinv_write_report(text,(unsigned)n,path,sizeof(path));
 if(result==8||nes_return_failed())nes_diag_blocked();
 /* No further SD access or game/menu path. Keep USB disabled for this session.
  * The already configured embedded-mini displays collection/save status only. */
 snes_bootprint_center(8,result?"TXT SAVE FAILED":"TXT SAVED + READBACK OK");
 snes_bootprint_center(11,"%s",path);
 snes_bootprint_center(13,"Save code: %d",result);
 snes_bootprint_center(16,"POWER OFF THEN COPY TXT");
 snes_bootprint_center(18,"MENU APPROVAL STILL PENDING");
 if(nes_return_failed())nes_diag_blocked();
 nes_diag_leave();
 snes_reset(0);
 for(;;)__NOP();
}
