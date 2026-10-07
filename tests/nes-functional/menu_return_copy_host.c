/* SPDX-License-Identifier: MIT */
/* Actual065 buffered copy; FatFS and PSRAM are fault-injectable models. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "mcu_loader_platform.h"
#include "nes_menu_return.h"
static uint8_t source[0x400201],ram[0x400000];
static unsigned size,fault,reads,writes,closes,progress;static bool sd_fault;
uint32_t nes_diag_ticks(void){return 0;}
bool nes_diag_sd_failed(void){return sd_fault;}
void nes_diag_observe(const struct nes_diag_report *r,bool a){(void)a;if(r->completed){assert(r->completed<=r->total);progress=r->completed;}}
FRESULT f_open(FIL *f,const char *p,unsigned m){assert(!strcmp(p,"menu")&&m==FA_READ);*f=(FIL){size,0};return fault==1;}
FRESULT f_lseek(FIL *f,uint32_t p){f->pos=p;return fault==2;}
FRESULT f_read(FIL *f,void *p,UINT n,UINT *got){reads++;memcpy(p,source+f->pos,n);f->pos+=n;*got=n-(fault==4);if(fault==7)f->fsize++;if(fault==10)sd_fault=true;return fault==3;}
FRESULT f_close(FIL *f){(void)f;closes++;return fault==5;}
uint16_t sram_writeblock(void *p,uint32_t a,uint16_t n){writes++;assert(a+n<=sizeof(ram));memcpy(ram+a,p,n);if(fault==9)nes_return_fail(NES_DIAG_SPI);return n-(fault==11);}
uint16_t sram_readblock(void *p,uint32_t a,uint16_t n){memcpy(p,ram+a,n);if(fault==6)((uint8_t *)p)[n-1]^=1;return n-(fault==12);}
static void setup(unsigned s,unsigned f){size=s;fault=f;reads=writes=closes=progress=0;sd_fault=false;nes_return_reset();nes_diag_begin();}
int main(void){
 setvbuf(stdout,0,_IONBF,0);unsigned cases=0;
 for(unsigned i=0;i<sizeof(source);i++)source[i]=(uint8_t)(i*73u+19u);
 const unsigned offsets[]={0,512,17};
 for(unsigned j=0;j<3;j++){
  unsigned n=j==2?257:8192;setup(n+offsets[j],0);
  assert(nes_return_copy_menu("menu",31,offsets[j])==n&&!nes_return_failed());
  assert(!memcmp(ram+31,source+offsets[j],n)&&progress==n&&closes==1);cases++;
 }
 setup(0x400000,0);assert(nes_return_copy_menu("menu",0,0)==0x400000&&writes==16384);cases++;
 for(unsigned f=1;f<=12;f++)if(f!=8){
  printf("COPY fault=%u\n",f);setup(768,f);assert(!nes_return_copy_menu("menu",0,0)&&nes_return_failed());
  assert(closes==(f!=1));if(f==6||f==9||f==11||f==12)assert(writes==1);cases++;
 }
 setup(0,0);assert(!nes_return_copy_menu("menu",0,0)&&!writes&&closes==1);cases++;
 setup(512,0);assert(!nes_return_copy_menu("menu",0,512)&&!writes);cases++;
 setup(0x400001,0);assert(!nes_return_copy_menu("menu",0,0)&&!reads);cases++;
 setup(512,0);assert(!nes_return_copy_menu("menu",0xffff00u,0)&&!reads);cases++;
 setup(512,0);nes_return_fail(NES_DIAG_SPI);assert(!nes_return_copy_menu("menu",0,0)&&!closes);cases++;
 printf("PASS MENU065 copy cases=%u max_bytes=4194304 readback=all bytes\n",cases);
 return 0;
}
