/* SPDX-License-Identifier: GPL-2.0-only */
/* Whole actual FatFS + actual069 write-permission helper/runtime.
 * Sector medium, CMD24, response CRC and data transmission are host models. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "ff.h"
#include "diskio.h"
#include "nes_menu_return.h"
#include "nes_sd_inventory.h"
#include "nes_sd_inventory_log073.h"
static unsigned char media[70000u*512u];
static FATFS fs;
static unsigned sectors,ticks,commands,writes,denials,fail_command,active_sector,budget,checks;
int sd_offload,ff_sd_offload,sd_offload_partial;
uint16_t sd_offload_partial_start,sd_offload_partial_end;
volatile enum diskstates disk_state;
static bool nes_diag_sd_fault;
static unsigned wp,ccs=1,during_blocktrans;
static uint8_t rsp[6];
#define MAX_CARDS 1
#define SDCARD_DETECT 1
#define SDCARD_WP wp
#define TRANS_NONE 0
static uint8_t crc7update(uint8_t c,uint8_t b){for(unsigned n=0;n<8;n++){c<<=1;if((b^c)&128)c^=9;b<<=1;}return c&127;}
static void nes_diag_sd_error(enum nes_diag_error);
static int cmd_fast(unsigned command,uint32_t address,unsigned ignored,void *data,uint8_t *response){
 (void)ignored;(void)data;assert(command==24&&address<sectors&&!nes_return_failed()&&nes_return_log_allowed());
 commands++;active_sector=address;if(commands==fail_command)return 0;
 memset(response,0,6);response[0]=24;uint8_t c=0;for(unsigned n=0;n<5;n++)c=crc7update(c,response[n]);response[5]=(uint8_t)((c<<1)|1);return 6;
}
static void send_datablock(uint8_t *p){assert(nes_return_log_allowed()&&!nes_return_failed());memcpy(media+active_sector*512u,p,512);writes++;}
#include "sd-permission-functions.inc"
void nes_diag_sd_reset(void){nes_diag_sd_fault=false;}
bool nes_diag_sd_failed(void){return nes_diag_sd_fault;}
uint32_t nes_diag_ticks(void){return ticks;}
void nes_diag_observe(const struct nes_diag_report *r,bool active){(void)r;(void)active;}
uint16_t sram_writeblock(void *p,uint32_t at,uint16_t n){(void)p;(void)at;(void)n;assert(!"unexpected menu SRAM write");return 0;}
uint16_t sram_readblock(void *p,uint32_t at,uint16_t n){(void)p;(void)at;(void)n;assert(!"unexpected menu SRAM read");return 0;}
DSTATUS disk_initialize(BYTE drv){assert(drv==0);return 0;}
DSTATUS disk_status(BYTE drv){assert(drv==0);return 0;}
DRESULT disk_read(BYTE drv,BYTE *p,DWORD sector,UINT count){
 /* Exact early rejection from the actual069 sdn_read entry, before media IO. */
#include "sd-read-rejection.inc"
 assert(!nes_return_failed()&&drv==0&&count&&sector+count<=sectors);
 memcpy(p,media+sector*512u,count*512u);if(budget)ticks+=1001;return RES_OK;
}
DRESULT disk_write(BYTE drv,const BYTE *p,DWORD sector,UINT count){
 assert(sector+count<=sectors);
 DRESULT r=nes_return_sd_write(drv,p,sector,count);if(r==RES_WRPRT)denials++;return r;
}
DRESULT disk_ioctl(BYTE drv,BYTE command,void *p){(void)p;assert(drv==0&&command==CTRL_SYNC);return nes_diag_sd_fault?RES_ERROR:RES_OK;}
DWORD get_fattime(void){return (DWORD)(2026-1980)<<25|10u<<21|7u<<16;}
static void word(unsigned at,unsigned n){media[at]=(uint8_t)n;media[at+1]=(uint8_t)(n>>8);}
static void dword(unsigned at,uint32_t n){for(unsigned i=0;i<4;i++)media[at+i]=(uint8_t)(n>>(8*i));}
static unsigned root_sector;
static void reset_case(unsigned fat32){
 nes_diag_leave();nes_return_reset();nes_diag_sd_reset();(void)f_mount(NULL,"",0);
 ticks=commands=writes=denials=fail_command=active_sector=budget=wp=during_blocktrans=sd_offload=ff_sd_offload=0;disk_state=DISK_OK;
 sectors=fat32?70000:8192;memset(media,0,sizeof(media));memset(&fs,0,sizeof(fs));
 media[0]=0xeb;media[1]=0x3c;media[2]=0x90;memcpy(media+3,"SDINFO  ",8);word(11,512);media[13]=1;media[16]=2;media[21]=0xf8;word(510,0xaa55);
 if(!fat32){memcpy(media+54,"FAT16   ",8);word(14,1);word(17,512);word(19,8192);word(22,32);root_sector=65;for(unsigned i=0;i<2;i++){word((1+i*32)*512,0xfff8);word((1+i*32)*512+2,0xffff);}}
 else {memcpy(media+82,"FAT32   ",8);word(14,32);dword(32,70000);dword(36,547);dword(44,2);word(48,1);root_sector=1126;
  for(unsigned i=0;i<2;i++){unsigned at=(32+i*547)*512;dword(at,0x0ffffff8);dword(at+4,0x0fffffff);dword(at+8,0x0fffffff);}
  dword(512,0x41615252);dword(512+484,0x61417272);dword(512+488,0xffffffff);dword(512+492,2);word(512+510,0xaa55);
 }
 assert(f_mount(&fs,"",1)==FR_OK&&fs.fs_type==(fat32?FS_FAT32:FS_FAT16));nes_diag_begin();nes_return_io_begin();
}
extern int sdinv_write_report072(const char *,unsigned,char *,size_t);
static char data[4500],path[16];
static void one(unsigned fat32){
 reset_case(fat32);int old=sdinv_write_report072(data,sizeof(data),path,sizeof(path));
 assert(old==4&&denials&&commands==0&&writes==0&&!nes_return_failed()&&!nes_return_log_allowed());
 assert(memcmp(media+root_sector*512u,"HW003000TXT",11));
 printf("REPRO072 FAT%u result=%d writes=%u denied=%u root_not_persisted=1\n",fat32?32:16,old,writes,denials);checks++;
 reset_case(fat32);assert(sdinv_write_report(data,sizeof(data),path,sizeof(path))==0&&!strcmp(path,"/HW004000.TXT"));
 assert(!nes_return_log_allowed()&&nes_diag_active()&&writes&&writes==commands&&!nes_return_failed());
 assert(!memcmp(media+root_sector*512u,"HW004000TXT",11));unsigned total=commands;
 FIL f;UINT got=0;char readback[4500];assert(f_open(&f,path,FA_READ)==FR_OK&&f_size(&f)==sizeof(data));
 assert(f_read(&f,readback,sizeof(readback),&got)==FR_OK&&got==sizeof(data)&&!memcmp(data,readback,sizeof(data))&&f_close(&f)==FR_OK);checks++;
 for(unsigned n=1;n<=total;n++){
  reset_case(fat32);fail_command=n;assert(sdinv_write_report(data,sizeof(data),path,sizeof(path))==8);
  assert(!nes_return_log_allowed()&&nes_diag_active()&&nes_return_failed()&&commands==n&&writes==n-1);checks++;
 }
 reset_case(fat32);wp=1;assert(sdinv_write_report(data,sizeof(data),path,sizeof(path))==4&&!commands&&!nes_return_log_allowed()&&!nes_return_failed());
 const struct sdinv_save_detail *d=sdinv_save_detail();assert(d->operation==2&&d->fresult==FR_DISK_ERR&&d->returned==0&&d->requested==256&&d->offset==0);checks++;
 reset_case(fat32);budget=1;assert(sdinv_write_report(data,sizeof(data),path,sizeof(path))==8&&!nes_return_log_allowed()&&nes_return_failed());checks++;
 reset_case(fat32);nes_diag_leave();assert(sdinv_write_report(data,sizeof(data),path,sizeof(path))==8&&!commands&&!nes_return_log_allowed());checks++;
 reset_case(fat32);nes_return_log_allow(true);assert(sdinv_write_report(data,sizeof(data),path,sizeof(path))==8&&!commands&&nes_return_log_allowed());nes_return_log_allow(false);checks++;
 reset_case(fat32);assert(sdinv_write_report(data,6144,path,sizeof(path))==1&&!commands&&!nes_return_log_allowed());checks++;
 printf("PASS073 FAT%u actual_FatFS_native_guard_runtime=1 command_fault_positions=%u\n",fat32?32:16,total);
}
int main(void){
#ifdef _WIN32
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);_set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);
#endif
 setvbuf(stdout,NULL,_IONBF,0);
 for(unsigned i=0;i<sizeof(data);i++)data[i]=(char)(i*7u);
 one(0);one(1);printf("PASS073 integration checks=%u no_physical_SD=1\n",checks);return 0;
}
