// SPDX-License-Identifier: MIT
// Synthetic FAT16 disk below the actual frozen227 FatFS; no hardware card IO.
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "ff.h"
#include "diskio.h"
enum { SECTORS=6000, FAT_SECTORS=24, ROOT_SECTOR=25, DATA_SECTOR=26 };
static uint8_t media[SECTORS*512u];
int sd_offload,ff_sd_offload,sd_offload_tgt,newcard,sd_offload_partial;
uint16_t sd_offload_partial_start,sd_offload_partial_end;
volatile enum diskstates disk_state=DISK_OK;
bool nes_diag_active(void){return false;}
bool nes_return_io_step(void){return true;}
static void word(uint8_t *p,uint32_t value){p[0]=(uint8_t)value;p[1]=(uint8_t)(value>>8);}
static void dword(uint8_t *p,uint32_t value){word(p,value);word(p+2,value>>16);}
void nrom_fatdisk_prepare(const uint8_t *file,uint32_t bytes){
 assert(bytes<=49u*512u);memset(media,0,sizeof(media));
 uint8_t *boot=media;boot[0]=0xeb;boot[1]=0x3c;boot[2]=0x90;memcpy(boot+3,"MSDOS5.0",8);
 word(boot+11,512);boot[13]=1;word(boot+14,1);boot[16]=1;word(boot+17,16);
 word(boot+19,SECTORS);boot[21]=0xf8;word(boot+22,FAT_SECTORS);word(boot+24,32);word(boot+26,64);
 boot[36]=0x80;boot[38]=0x29;memcpy(boot+54,"FAT16   ",8);boot[510]=0x55;boot[511]=0xaa;
 uint8_t *fat=media+512;word(fat,0xfff8);word(fat+2,0xffff);
 unsigned clusters=(bytes+511u)/512u;
 for(unsigned i=0;i<clusters;i++)word(fat+(i+2)*2u,i+1==clusters?0xffff:i+3);
 uint8_t *dir=media+ROOT_SECTOR*512u;memcpy(dir,"NROM    NES",11);dir[11]=0x20;word(dir+26,2);dword(dir+28,bytes);
 memcpy(media+DATA_SECTOR*512u,file,bytes);
}
void nrom_fatdisk_mutate(uint32_t offset){assert(offset<49u*512u);media[DATA_SECTOR*512u+offset]^=1;}
DSTATUS disk_initialize(BYTE drive){return drive?STA_NOINIT:0;}
DSTATUS disk_status(BYTE drive){return drive?STA_NOINIT:0;}
DRESULT disk_read(BYTE drive,BYTE *buff,DWORD sector,UINT count){
 if(drive||!count||sector>=SECTORS||count>SECTORS-sector)return RES_PARERR;
 memcpy(buff,media+sector*512u,count*512u);return RES_OK;
}
DRESULT disk_write(BYTE drive,const BYTE *buff,DWORD sector,UINT count){(void)drive;(void)buff;(void)sector;(void)count;return RES_WRPRT;}
DRESULT disk_ioctl(BYTE drive,BYTE cmd,void *buff){(void)drive;(void)cmd;(void)buff;return RES_PARERR;}
DWORD get_fattime(void){return 0;}
