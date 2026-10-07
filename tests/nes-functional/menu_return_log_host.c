/* SPDX-License-Identifier: MIT */
/* Actual menu lifecycle. Each setup models a fresh MCU invocation. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "mcu_loader_platform.h"
#include "nes_menu_return.h"
#include "nes_menu_diagnostic.c"
static unsigned irq,held,mode,opens,writes,closes;static bool native_fault;
uint32_t nes_diag_ticks(void){return 0;}
bool nes_diag_sd_failed(void){return native_fault;}
void nes_diag_sd_reset(void){native_fault=false;}
void nes_diag_observe(const struct nes_diag_report *r,bool a){(void)r;if(a)assert(!irq);}
unsigned NVIC_GetEnableIRQ(int n){(void)n;return irq;}
void NVIC_DisableIRQ(int n){(void)n;irq=0;}
void NVIC_EnableIRQ(int n){(void)n;irq=1;}
void snes_reset(int n){held=n;}
bool nes_menu_sd_probe(const char *p,const char *image,bool c,struct nes_menu_probe_report *r){(void)p;(void)image;(void)c;memset(r,0,sizeof(*r));r->sd.verified=true;return mode!=1;}
FRESULT f_open(FIL *f,const char *p,unsigned m){(void)f;(void)p;assert(m==(FA_WRITE|FA_CREATE_ALWAYS)&&!irq&&held&&nes_diag_active()&&nes_return_log_allowed());opens++;if(mode==4)native_fault=true;return mode==3||mode==4;}
FRESULT f_write(FIL *f,const void *p,UINT n,UINT *got){(void)f;(void)p;assert(nes_return_log_allowed());writes++;*got=n-(mode==6);if(mode==7)native_fault=true;return mode==5||mode==7;}
FRESULT f_close(FIL *f){(void)f;closes++;if(mode==9)native_fault=true;return mode==8||mode==9;}
FRESULT f_lseek(FIL *f,uint32_t a){(void)f;(void)a;assert(0);return 1;}
FRESULT f_read(FIL *f,void *p,UINT n,UINT *g){(void)f;(void)p;(void)n;(void)g;assert(0);return 1;}
uint16_t sram_writeblock(void *p,uint32_t a,uint16_t n){(void)p;(void)a;(void)n;assert(0);return 0;}
uint16_t sram_readblock(void *p,uint32_t a,uint16_t n){(void)p;(void)a;(void)n;assert(0);return 0;}
int main(void){setvbuf(stdout,0,_IONBF,0);unsigned cases=0;
 for(unsigned m=0;m<12;m++)for(unsigned enabled=0;enabled<2;enabled++){
  printf("LOG fault=%u irq=%u\n",m,enabled);pending=safe_to_reload=prepared=false; /* External MCU reset, no product retry. */
  mode=m;irq=enabled;held=opens=writes=closes=0;nes_diag_leave();
  bool safe=nes_menu_diagnostic_run((const uint8_t *)"NES VERIFY 065 80.nh1");
  assert(safe==(m!=1)&&!irq&&held&&nes_diag_active());
  if(m==10)nes_return_fail(NES_DIAG_SPI);if(m==11)nes_return_fail(NES_DIAG_TIMER);
  bool ready=nes_menu_diagnostic_prepared(m!=2);
  bool blocked=m==1||m==2||m==4||m==7||m==9||m>=10;
  assert(ready==!blocked&&!nes_return_log_allowed()&&!irq&&held&&nes_diag_active());
  if(m==1||m==2||m>=10)assert(!opens);
  unsigned before=opens;
  if(ready)held=0;
  nes_menu_diagnostic_released();assert(opens==before); /* No SD after release. */
  if(blocked)assert(held&&!irq&&pending&&nes_diag_active());
  else assert(!held&&irq==enabled&&!pending&&!nes_diag_active());
  cases++;
 }
 printf("PASS MENU065 log cases=%u native_fault_blocks_release=1 optional_log_failure=1 no_SD_after_release=1\n",cases);
 return 0;
}
