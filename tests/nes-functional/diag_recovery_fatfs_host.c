/* SPDX-License-Identifier: MIT */
/* Actual pinned FatFS f_read/validate/clust2sect and064 sdn_read.
 * File objects, FAT chain and the SD command/card are host inputs. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "ff.h"
#include "diskio.h"
#include "nes_diag_runtime.h"
#define MAX_CARDS 1
#define READ_SINGLE_BLOCK 17
#define STOP_TRANSMISSION 12
#define CRC_ERROR -1
#define SDCARD_DETECT 1
int sd_offload,ff_sd_offload,sd_offload_partial;
uint16_t sd_offload_partial_start,sd_offload_partial_end;
volatile enum diskstates disk_state;
enum {TRANS_NONE,TRANS_READ,TRANS_WRITE,TRANS_MID};
static unsigned during_blocktrans,ccs=1,commands,fail_at,legacy_reads;
static uint8_t rsp[17];static bool nes_diag_sd_fault;
static void nes_diag_sd_error(enum nes_diag_error);
uint32_t nes_diag_ticks(void){return 0;}
void nes_diag_observe(const struct nes_diag_report *r,bool a){(void)r;(void)a;}
static uint8_t crc7update(uint8_t crc,uint8_t data){for(unsigned n=0;n<8;n++){crc<<=1;if(data&0x80)crc^=0x80;if(crc&0x80)crc^=9;data<<=1;}return crc;}
static int cmd_fast(uint8_t command,uint32_t address,uint8_t crc,uint8_t *data,uint8_t *reply){
 (void)address;(void)crc;commands++;if(commands==fail_at)return CRC_ERROR;
 memset(reply,0,6);reply[0]=command;uint8_t c=0;for(unsigned n=0;n<5;n++)c=crc7update(c,reply[n]);reply[5]=(uint8_t)((c<<1)|1);
 if(data)memset(data,0x34,512);
 return 6;
}
#include "nes_diag_sd.inc"
static void read_block(DWORD sector,BYTE *buffer){(void)sector;(void)buffer;legacy_reads++;assert(0);}
static void readled(unsigned n){(void)n;}
#include "sd-read-function.inc"
DRESULT disk_read(BYTE drv,BYTE *buffer,DWORD sector,UINT count){return sdn_read(drv,buffer,sector,count);}
DSTATUS disk_status(BYTE drv){assert(!drv);return nes_diag_sd_fault?STA_NOINIT:0;}
DRESULT disk_write(BYTE drv,const BYTE *buffer,DWORD sector,UINT count){(void)drv;(void)buffer;(void)sector;(void)count;assert(0);return RES_ERROR;}
#define SS(fs) 512u
#define ENTER_FF(fs) ((void)0)
#define LEAVE_FF(fs,res) return res
#define ABORT(fs,res) do{fp->err=(BYTE)(res);return res;}while(0)
static void mem_cpy(void *d,const void *s,UINT n){memcpy(d,s,n);}
static DWORD get_fat(FATFS *fs,DWORD cluster){(void)fs;return cluster+1;}
static DWORD clmt_clust(FIL *f,DWORD pos){(void)f;(void)pos;assert(0);return 0;}
#include "fatfs-read-functions.inc"
static void setup(FATFS *fs,FIL *f,unsigned fail){
 memset(fs,0,sizeof(*fs));fs->fs_type=3;fs->id=7;fs->csize=1;fs->n_fatent=10;fs->database=2;
 memset(f,0,sizeof(*f));f->fs=fs;f->id=7;f->flag=FA_READ;f->sclust=2;f->fsize=1024;
 fail_at=fail;commands=legacy_reads=sd_offload=ff_sd_offload=sd_offload_partial=during_blocktrans=0;disk_state=DISK_OK;nes_diag_sd_reset();nes_diag_begin();
}
int main(void){
 FATFS fs;FIL f;uint8_t data[1024];UINT got=0;unsigned cases=0;
 _Static_assert(sizeof(DWORD)==4,"FatFS DWORD must be32bit");
 setup(&fs,&f,0);assert(f_read(&f,data,1024,&got)==FR_OK&&got==1024&&commands==2&&!legacy_reads&&data[1023]==0x34);cases++;
 setup(&fs,&f,0);assert(f_read(&f,data,256,&got)==FR_OK&&got==256&&commands==1);assert(f_read(&f,data,256,&got)==FR_OK&&got==256&&commands==1);cases++;
 setup(&fs,&f,1);memset(data,0xaa,sizeof(data));assert(f_read(&f,data,512,&got)==FR_DISK_ERR&&!got&&f.err==FR_DISK_ERR&&commands==1&&data[0]==0xaa);cases++;
 assert(f_read(&f,data,512,&got)==FR_NOT_READY&&!got&&commands==1);cases++;
 setup(&fs,&f,2);assert(f_read(&f,data,1024,&got)==FR_DISK_ERR&&got==512&&f.err==FR_DISK_ERR&&commands==2&&nes_diag_status()->error==NES_DIAG_SD_CRC);cases++;
 setup(&fs,&f,0);ff_sd_offload=1;assert(f_read(&f,data,256,&got)==FR_DISK_ERR&&!got&&!commands&&nes_diag_status()->error==NES_DIAG_SD_STATE);cases++;
 printf("PASS RECOVERY064 FatFS cases=%u actual_f_read=1 partial_error=1 no_retry=1\n",cases);return 0;
}
