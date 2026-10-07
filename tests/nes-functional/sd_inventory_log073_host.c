/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include "sd_inventory_ff_mock.h"
#include "nes_sd_inventory.h"
#include "nes_sd_inventory_log073.h"
static bool window;
static unsigned opened_windows,closed_windows;
bool nes_diag_active(void){return true;}
bool nes_return_log_allowed(void){return window;}
void nes_return_log_allow(bool b){window=b;if(b)opened_windows++;else closed_windows++;}
static uint8_t stored[6144];static unsigned length,existing,fault,opens,closes,writes,reads,syncs,blocked,steps,limit;
bool nes_return_failed(void){return blocked!=0;}
bool nes_return_io_step(void){steps++;return !limit||steps<limit;}
FRESULT f_open(FIL *f,const char *p,unsigned mode){assert(!blocked&&window);opens++;unsigned slot=0;assert(sscanf(p,"/HW004%3u.TXT",&slot)==1&&slot<1000);*f=(FIL){length,0,mode};if(mode==(FA_WRITE|FA_CREATE_NEW)){if(slot<existing)return FR_EXIST;if(fault==1)return 2;length=0;}else {assert(mode==FA_READ);if(fault==6)return 2;}return 0;}
FRESULT f_write(FIL *f,const void *p,UINT n,UINT *got){assert(!blocked&&window&&f->mode==(FA_WRITE|FA_CREATE_NEW)&&length+n<sizeof(stored));writes++;*got=fault==2?n-1:n;memcpy(stored+length,p,*got);length+=*got;if(fault==10){blocked=1;return 2;}return fault==3?2:0;}
FRESULT f_sync(FIL *f){(void)f;assert(!blocked&&window);syncs++;if(fault==11)blocked=1;return fault==4?2:0;}
FRESULT f_close(FIL *f){assert(!blocked&&window);closes++;if(fault==12)blocked=1;return fault==5||(fault==9&&f->mode==FA_READ)?2:0;}
FRESULT f_read(FIL *f,void *p,UINT n,UINT *got){assert(!blocked&&window&&f->mode==FA_READ&&f->pos+n<=length);reads++;*got=fault==8?n-1:n;memcpy(p,stored+f->pos,*got);f->pos+=*got;if(fault==7)((uint8_t*)p)[0]^=1;return 0;}
int main(void){
 unsigned checks=0;char data[4500],path[16];memset(data,'A',sizeof(data));
 unsigned expected[]={0,2,4,4,5,6,7,7,7,7,8,8,8};
 for(unsigned i=0;i<13;i++){
  length=opens=closes=writes=reads=syncs=blocked=steps=limit=0;existing=3;fault=i;
  assert(sdinv_write_report(data,sizeof(data),path,sizeof(path))==(int)expected[i]);
  assert(!window&&opened_windows==closed_windows);
  if(!i)assert(!memcmp(data,stored,sizeof(data))&&closes==2&&writes==18&&reads==18&&!strcmp(path,"/HW004003.TXT"));
  if(i>=10)assert(blocked&&closes==(i==12?1:0));
  if(i==2){const struct sdinv_save_detail*d=sdinv_save_detail();assert(d->failed&&d->operation==2&&d->fresult==0&&d->returned==255&&d->requested==256&&d->offset==0);}
  checks++;
 }
 for(unsigned i=1;i<=8;i++){
  length=opens=closes=writes=reads=syncs=blocked=steps=0;limit=i;existing=3;fault=0;
  assert(sdinv_write_report(data,sizeof(data),path,sizeof(path))==8);checks++;
 }
 length=opens=closes=writes=reads=syncs=blocked=steps=limit=0;existing=1000;fault=0;
 assert(sdinv_write_report(data,sizeof(data),path,sizeof(path))==3&&opens==1000&&!writes&&!closes);checks++;
 assert(sdinv_write_report(data,6144,path,sizeof(path))==1);checks++;
 printf("PASS073 writer checks=%u CREATE_NEW=1 sync_close_allbyte_readback=1 native_no_extra_IO=1\n",checks);return 0;
}
