/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <setjmp.h>
#include "sd_inventory_mock_hw.h"
#include "sd_inventory_ff_mock.h"
#include "nes_sd_inventory.h"
#include "nes_sd_inventory_log073.h"
static const struct sdinv_save_detail detail={0};
const struct sdinv_save_detail *sdinv_save_detail(void){return &detail;}
#include "nes_menu_return.h"
int sd_offload,ff_sd_offload;
static jmp_buf end;static unsigned mode,reset,usb_off,fault,screens,collects,formats,writes,blocked,finished,leave_count;
void NVIC_DisableIRQ(unsigned n){assert(n==OTG_FS_IRQn);usb_off=1;}
void snes_reset(int n){reset=n;}
void snes_bootclear(void){}
void snes_bootprint_version(void){}
void snes_bootprint_center(int line,const char *fmt,...){(void)fmt;screens++;if(line==18){assert(nes_diag_active());if(mode==5)fault=1;}}
void mock_halt(void){finished=1;longjmp(end,1);}
void nes_return_reset(void){fault=0;}
void nes_diag_sd_reset(void){}
void nes_return_io_begin(void){assert(reset&&usb_off&&nes_diag_active());}
bool nes_return_io_step(void){return !fault;}
bool nes_return_failed(void){return fault!=0;}
void nes_diag_blocked(void){blocked=1;assert(reset&&usb_off&&nes_diag_active());longjmp(end,1);}
uint32_t nes_diag_ticks(void){return 0;}
void nes_diag_observe(const struct nes_diag_report *r,bool active){(void)r;if(!active)leave_count++;}
int sdinv_collect(const struct sdinv_io *io,struct sdinv_report *r){(void)io;memset(r,0,sizeof(*r));collects++;assert(reset&&usb_off&&nes_diag_active()&&!sd_offload&&!ff_sd_offload);if(mode==1)fault=1;return mode!=1;}
int sdinv_format(const struct sdinv_report *r,char *p,size_t n){(void)r;(void)n;formats++;memcpy(p,"TXT",3);return mode==4?-1:3;}
int sdinv_write_report(const char *p,unsigned n,char *path,size_t size){(void)p;(void)n;assert(size==16);writes++;strcpy(path,"/HW004000.TXT");if(mode==2){fault=1;return 8;}return mode==3?4:0;}
/* The actual session's reader callbacks are linked but collection is mocked.
 * Any accidental direct FatFS access in the platform/session fails here. */
FRESULT f_open(FIL *f,const char *p,unsigned n){(void)f;(void)p;(void)n;assert(0);return 2;}
FRESULT f_read(FIL *f,void *p,UINT n,UINT *got){(void)f;(void)p;(void)n;(void)got;assert(0);return 2;}
FRESULT f_close(FIL *f){(void)f;assert(0);return 2;}
FRESULT f_lseek(FIL *f,uint32_t n){(void)f;(void)n;assert(0);return 2;}
int main(void){
 for(mode=0;mode<6;mode++){
  reset=usb_off=fault=screens=collects=formats=writes=blocked=finished=leave_count=0;sd_offload=ff_sd_offload=1;
  if(!setjmp(end))sdinv_run();
  assert(collects==1&&usb_off);
  if(mode==1||mode==2||mode==5){assert(blocked&&!finished&&reset&&!leave_count);}
  else {assert(!blocked&&finished&&!reset&&leave_count==1);}
  if(mode==1)assert(!formats&&!writes&&screens==2);
  if(mode==4)assert(!writes);
 }
 printf("PASS073 actual_platform sessions=6 RESET_USB=1 no_SD_after_fault=1 screen_guard=1 no_menu_core_route=1\n");return 0;
}
