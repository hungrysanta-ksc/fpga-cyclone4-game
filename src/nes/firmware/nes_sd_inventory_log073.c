/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdio.h>
#include <string.h>
#include "nes_sd_inventory.h"
#include "nes_sd_inventory_log073.h"
#include "nes_menu_return.h"
#ifdef SDINFO_HOST_TEST
#include "sd_inventory_ff_mock.h"
#else
#include "ff.h"
#endif
static struct sdinv_save_detail detail;
const struct sdinv_save_detail *sdinv_save_detail(void){return &detail;}
static void record(unsigned op,FRESULT r,unsigned want,unsigned got,unsigned offset){
 if(detail.failed)return;
 detail=(struct sdinv_save_detail){op,(unsigned)r,want,got,offset,r!=FR_OK||want!=got};
}
static int allowed(void){return !nes_return_failed()&&nes_return_io_step();}
static int write_report(const char *report,unsigned len,char *path,size_t size){
 FIL f;UINT got=0;int result=0;unsigned slot;path[0]=0;
 for(slot=0;slot<1000;slot++){
  if(!allowed())return 8;
  snprintf(path,size,"/HW004%03u.TXT",slot);
  FRESULT r=f_open(&f,path,FA_WRITE|FA_CREATE_NEW);
  if(r!=FR_EXIST)record(1,r,0,0,0);
  if(nes_return_failed())return 8;
  if(r==FR_OK)break;
  if(r!=FR_EXIST)return 2;
 }
 if(slot==1000){path[0]=0;return 3;}
 for(unsigned pos=0;pos<len;){
  unsigned n=len-pos;if(n>256)n=256;
  if(!allowed())return 8;
  got=0;FRESULT r=f_write(&f,report+pos,n,&got);record(2,r,n,got,pos);
  if(nes_return_failed())return 8;
  if(r!=FR_OK||got!=n){result=4;break;}pos+=n;
 }
 if(!result){if(!allowed())return 8;FRESULT r=f_sync(&f);record(3,r,0,0,len);if(r!=FR_OK)result=5;}
 if(!allowed())return 8;
 FRESULT r=f_close(&f);record(4,r,0,0,len);if(r!=FR_OK&&!result)result=6;
 if(nes_return_failed())return 8;
 if(result)return result;
 if(!allowed())return 8;
 r=f_open(&f,path,FA_READ);record(5,r,0,0,len);
 if(r!=FR_OK)return nes_return_failed()?8:7;
 if(nes_return_failed())return 8;
 if(f_size(&f)!=len){record(8,FR_OK,len,(unsigned)f_size(&f),0);result=7;}
 uint8_t data[256];
 for(unsigned pos=0;!result&&pos<len;){
  unsigned n=len-pos;if(n>sizeof(data))n=sizeof(data);
  if(!allowed())return 8;
  got=0;r=f_read(&f,data,n,&got);record(6,r,n,got,pos);
  if(nes_return_failed())return 8;
  if(r!=FR_OK||got!=n||memcmp(data,report+pos,n)){detail.failed=1;result=7;break;}pos+=n;
 }
 if(!allowed())return 8;
 r=f_close(&f);record(7,r,0,0,len);if(r!=FR_OK)result=7;
 return nes_return_failed()?8:result;
}
int sdinv_write_report(const char *report,unsigned len,char *path,size_t size){
 detail=(struct sdinv_save_detail){0};
 if(!len||len>=6144||size<14)return 1;
 if(!nes_diag_active()||nes_return_failed()||nes_return_log_allowed())return 8;
 /* Same bounded native SD path as069: only this report owns write permission.
  * Always revoke it, including native faults; revocation itself performs no IO. */
 nes_return_log_allow(true);
 int result=write_report(report,len,path,size);
 nes_return_log_allow(false);
 return result;
}
