/* SPDX-License-Identifier: MIT */
#include <string.h>
#include "config.h"
#include "fileops.h"
#include "memory.h"
#include "nes_menu_return.h"
static bool fault,log_allowed,io_active;
static struct nes_diag_wait io_wait;
void nes_return_reset(void){fault=log_allowed=io_active=false;}
void nes_return_io_begin(void){io_active=true;io_wait=nes_diag_wait_start(6000,1000000u);}
bool nes_return_io_step(void){
 if(nes_return_failed())return false;
 if(io_active&&!nes_diag_wait_step(&io_wait)){nes_return_fail(NES_DIAG_MENU);return false;}
 return true;
}
void nes_return_fail(enum nes_diag_error error){fault=true;nes_diag_fail(error);}
bool nes_return_failed(void){return fault||nes_diag_sd_failed();}
void nes_return_log_allow(bool allow){log_allowed=allow;if(allow){io_active=true;io_wait=nes_diag_wait_start(1000,10000u);}}
bool nes_return_log_allowed(void){return log_allowed;}
uint32_t nes_return_copy_menu(const char *path,uint32_t address,uint32_t offset) {
 FIL file;uint8_t data[256],verify[256];UINT got=0;uint32_t copied=0;
 if(nes_return_failed())return 0;
 FRESULT r=f_open(&file,path,FA_READ);
 if(r!=FR_OK){nes_return_fail(NES_DIAG_MENU);return 0;}
 uint32_t size=f_size(&file);
 bool ok=size>offset&&size-offset<=0x400000u&&address<=0xffffffu-(size-offset-1u);
 if(ok)ok=f_lseek(&file,offset)==FR_OK;
 while(ok&&copied<size-offset){
  UINT n=size-offset-copied;if(n>sizeof(data))n=sizeof(data);
  r=f_read(&file,data,n,&got);
  if(r!=FR_OK||got!=n){ok=false;break;}
  if(sram_writeblock(data,address+copied,(uint16_t)n)!=n||nes_return_failed()){ok=false;break;}
  if(sram_readblock(verify,address+copied,(uint16_t)n)!=n||nes_return_failed()||memcmp(data,verify,n)){ok=false;break;}
  copied+=n;nes_diag_progress(NES_DIAG_RECOVER,copied,size-offset);
 }
 if(f_size(&file)!=size)ok=false;
 if(f_close(&file)!=FR_OK)ok=false;
 if(!ok){nes_return_fail(NES_DIAG_MENU);return 0;}
 return copied;
}
