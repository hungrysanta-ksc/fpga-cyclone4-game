/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
#include <crtdbg.h>
#include "fileops.h"
#include "nes_menu_return.h"
#include "nes_menu076.h"
#include "fpga_spi.h"
FIL file_handle;FRESULT file_res;static snes_romprops_t romprops;
static uint8_t image[65536],original[65536],ram[65536];
static unsigned size,mode,fail_at,reads,writes,closes,opens,cases;static bool sd_fault;static uint32_t ticks,tick_step;
enum {GOOD,OPEN,SEEK,SHORT_READ_FAULT,READ,SHARED,CLOSE,SIZE_CHANGE_FAULT,VERIFY,SPI,WRITE_SHORT,READ_SHORT,SEEK_LIE,SHARED_OPEN,SHARED_SEEK,SHARED_CLOSE};
uint32_t nes_diag_ticks(void){ticks+=tick_step;return ticks;}
bool nes_diag_sd_failed(void){return sd_fault;}
void nes_diag_observe(const struct nes_diag_report *r,bool a){(void)r;(void)a;}
FRESULT f_open(FIL *f,const char *p,unsigned flags){assert(!sd_fault&&p&&flags==FA_READ);opens++;*f=(FIL){size,0};if(mode==SHARED_OPEN)sd_fault=true;return mode==OPEN;}
FRESULT f_lseek(FIL *f,uint32_t at){assert(!sd_fault);f->fptr=at+(mode==SEEK_LIE);if(mode==SHARED_SEEK)sd_fault=true;return mode==SEEK;}
FRESULT f_read(FIL *f,void *p,UINT n,UINT *got){
 assert(!sd_fault);reads++;assert(f->fptr+n<=sizeof(image));memcpy(p,image+f->fptr,n);f->fptr+=n;*got=n;
 if(reads==fail_at){if(mode==SHORT_READ_FAULT)*got=n-1;if(mode==READ)return 1;if(mode==SHARED)sd_fault=true;if(mode==SIZE_CHANGE_FAULT)f->fsize++;}return 0;
}
FRESULT f_close(FIL *f){(void)f;assert(!sd_fault);closes++;if(mode==SHARED_CLOSE)sd_fault=true;return mode==CLOSE;}
void file_close(void){file_res=f_close(&file_handle);}
uint16_t sram_writeblock(void *p,uint32_t a,uint16_t n){assert(!sd_fault&&a+n<=sizeof(ram));memcpy(ram+a,p,n);writes++;if(mode==SPI)nes_return_fail(NES_DIAG_SPI);return n-(mode==WRITE_SHORT);}
uint16_t sram_readblock(void *p,uint32_t a,uint16_t n){assert(!sd_fault&&a+n<=sizeof(ram));memcpy(p,ram+a,n);if(mode==VERIFY)((uint8_t*)p)[0]^=1;return n-(mode==READ_SHORT);}
#include "active-memory.inc"
static void setup(unsigned fault,unsigned at){
 memcpy(image,original,sizeof(image));mode=fault;fail_at=at;size=sizeof(image);reads=writes=closes=opens=0;ticks=tick_step=0;sd_fault=false;file_handle=(FIL){size,0};file_res=0;
 nes_return_reset();nes_diag_begin();nes_return_io_begin();memset(&romprops,0xa5,sizeof(romprops));
}
int main(int argc,char **argv){
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);_set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);setvbuf(stdout,0,_IONBF,0);
 assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f&&fread(original,1,sizeof(original),f)==sizeof(original)&&!fclose(f));
 setup(GOOD,0);assert(memory_classify()&&!nes_return_failed()&&reads==256&&closes==1);assert(nes_menu_approved076(&romprops)&&romprops.fpga_features==FEAT_SRTC);cases++;
 assert(nes_return_copy_menu("menu",0,0)==65536&&writes==256&&closes==2&&!memcmp(ram,original,65536));cases++;
 /* The new path initializes flags instead of retaining a previous ROM. */
 assert(romprops.expramsize_bytes==1024&&!romprops.error&&!romprops.fpga_conf);cases++;
 setup(GOOD,0);image[100]^=1;puts("class_crc_reject");assert(!memory_classify()&&nes_return_failed()&&!closes);cases++;
 setup(GOOD,0);assert(memory_classify());image[100]^=1;puts("copy_crc_reject");assert(!nes_return_copy_menu("menu",0,0)&&nes_return_failed());cases++;
 for(unsigned fault=SHORT_READ_FAULT;fault<=SHARED;fault++)for(unsigned at=1;at<=256;at++){
  setup(fault,at);assert(!memory_classify()&&nes_return_failed()&&reads==at&&!closes&&!writes);cases++;
 }
 for(unsigned fault=SEEK;fault<=SEEK_LIE;fault++){
  if(fault!=SEEK&&fault!=CLOSE&&fault!=SIZE_CHANGE_FAULT&&fault!=SEEK_LIE)continue;
  setup(fault,256);assert(!memory_classify()&&nes_return_failed());cases++;
 }
 const unsigned lengths[]={0,65535,65537};
 for(unsigned i=0;i<3;i++){setup(GOOD,0);file_handle.fsize=lengths[i];assert(!memory_classify()&&!reads&&nes_return_failed());cases++;}
 const unsigned fields[]={0xffd5,0xffd6,0xffd7,0xffd8,0xffbd,0xfffc,0xff02};
 for(unsigned i=0;i<7;i++){setup(GOOD,0);image[fields[i]]^=0x80;assert(!memory_classify()&&nes_return_failed());cases++;}
 setup(GOOD,0);assert(memory_classify());romprops.has_sa1=1;assert(!nes_menu_approved076(&romprops));cases++;
 setup(GOOD,0);nes_return_fail(NES_DIAG_SPI);assert(!memory_classify()&&!reads&&!closes);cases++;
 setup(GOOD,0);tick_step=6000;assert(!memory_classify()&&!reads&&nes_return_failed());cases++;
 const unsigned positions[]={1,2,128,255,256};
 for(unsigned fault=OPEN;fault<=READ_SHORT;fault++)for(unsigned i=0;i<5;i++){
  setup(fault,positions[i]);assert(!nes_return_copy_menu("menu",0,0)&&nes_return_failed());
  if(fault==SHARED)assert(reads==positions[i]&&writes==positions[i]-1&&!closes);cases++;
 }
 setup(GOOD,0);assert(!nes_return_copy_menu("menu",1,0)&&!reads);cases++;
 setup(GOOD,0);assert(!nes_return_copy_menu("menu",0,512)&&!reads);cases++;
 setup(GOOD,0);tick_step=6000;assert(!nes_return_copy_menu("menu",0,0)&&!reads);cases++;
 for(unsigned fault=SHARED_OPEN;fault<=SHARED_CLOSE;fault++){
  setup(fault,0);assert(!nes_return_copy_menu("menu",0,0)&&sd_fault&&nes_return_failed());assert(closes==(fault==SHARED_CLOSE));cases++;
 }
 for(unsigned fault=SHARED_SEEK;fault<=SHARED_CLOSE;fault++){
  setup(fault,0);assert(!memory_classify()&&sd_fault&&nes_return_failed());cases++;
 }
 printf("PASS076 checks=%u classified_reads256 copied65536 fault_each_read768 native_no_followup=1 physical=0\n",cases);return 0;
}
