/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdio.h>
#include <string.h>
#include "nes_sd_inventory.h"
#include "nes_menu_return.h"
#ifdef SDINFO_HOST_TEST
#include "sd_inventory_ff_mock.h"
#else
#include "ff.h"
#endif
static int allowed(void){return !nes_return_failed()&&nes_return_io_step();}
/* 0 saved+all-byte readback; 1 format,2 open,3 full,4 write,5 sync,
 * 6 close,7 readback,8 shared fault/budget (no further IO, even close). */
int sdinv_write_report(const char *report,unsigned len,char *path,size_t size){
 if(!len||len>=6144||size<14)return 1;
 FIL f;UINT got=0;int result=0;unsigned slot;path[0]=0;
 for(slot=0;slot<1000;slot++){
  if(!allowed())return 8;
  snprintf(path,size,"/HW003%03u.TXT",slot);
  FRESULT r=f_open(&f,path,FA_WRITE|FA_CREATE_NEW);
  if(nes_return_failed())return 8;
  if(r==FR_OK)break;
  if(r!=FR_EXIST)return 2;
 }
 if(slot==1000){path[0]=0;return 3;}
 for(unsigned pos=0;pos<len;){
  unsigned n=len-pos;if(n>256)n=256;
  if(!allowed())return 8;
  FRESULT r=f_write(&f,report+pos,n,&got);
  if(nes_return_failed())return 8;
  if(r!=FR_OK||got!=n){result=4;break;}pos+=n;
 }
 if(!result){if(!allowed())return 8;if(f_sync(&f)!=FR_OK)result=5;}
 if(!allowed())return 8;
 if(f_close(&f)!=FR_OK&&!result)result=6;
 if(nes_return_failed())return 8;
 if(result)return result;
 if(!allowed())return 8;
 if(f_open(&f,path,FA_READ)!=FR_OK)return nes_return_failed()?8:7;
 if(nes_return_failed())return 8;
 if(f_size(&f)!=len)result=7;
 uint8_t data[256];
 for(unsigned pos=0;!result&&pos<len;){
  unsigned n=len-pos;if(n>sizeof(data))n=sizeof(data);
  if(!allowed())return 8;
  FRESULT r=f_read(&f,data,n,&got);
  if(nes_return_failed())return 8;
  if(r!=FR_OK||got!=n||memcmp(data,report+pos,n)){result=7;break;}pos+=n;
 }
 if(!allowed())return 8;
 if(f_close(&f)!=FR_OK)result=7;
 return nes_return_failed()?8:result;
}
