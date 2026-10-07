/* SPDX-License-Identifier: MIT */
/* Actual guarded FatFS cache/allocation helpers. FAT and card are models. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "ff.h"
#include "diskio.h"
#include "nes_menu_return.h"
#define SS(fs) 512u
#define FS_FAT12 1
#define FS_FAT16 2
#define FS_FAT32 3
static unsigned reads;static uint32_t ticks,step;
uint32_t nes_diag_ticks(void){ticks+=step;return ticks;}
bool nes_diag_sd_failed(void){return false;}
void nes_diag_observe(const struct nes_diag_report *r,bool a){(void)r;(void)a;}
static FRESULT sync_window(FATFS *fs){(void)fs;return FR_OK;}
DRESULT disk_read(BYTE d,BYTE *p,DWORD s,UINT n){(void)d;(void)s;assert(n==1);reads++;for(unsigned i=0;i<512;i+=2){p[i]=2;p[i+1]=0;}return RES_OK;}
#include "fatfs-cache-functions.inc"
static void setup(FATFS *fs){memset(fs,0,sizeof(*fs));fs->fs_type=FS_FAT16;fs->n_fatent=30000;fs->last_clust=2;fs->winsect=fs->fatbase=1;fs->free_clust=UINT32_MAX;for(unsigned i=0;i<512;i+=2)fs->win[i]=2;reads=ticks=step=0;nes_return_reset();nes_diag_begin();}
int main(void){setvbuf(stdout,0,_IONBF,0);unsigned cases=0;FATFS fs;
 setup(&fs);assert(get_fat(&fs,2)==2&&!reads&&!nes_return_failed());cases++;
 printf("FATFS cached budget\n");setup(&fs);nes_return_log_allow(true);unsigned n;
 for(n=0;n<10001;n++)if(get_fat(&fs,2)==UINT32_MAX)break;
 assert(n<10001&&!reads&&nes_return_failed());cases++;
 setup(&fs);nes_return_log_allow(true);assert(create_chain(&fs,0)==UINT32_MAX&&nes_return_failed()&&reads<50);cases++;
 setup(&fs);nes_return_log_allow(true);fs.win[6]=0;assert(create_chain(&fs,0)==3&&!nes_return_failed()&&fs.wflag);cases++;
 setup(&fs);ticks=UINT32_MAX-1;step=500;nes_return_log_allow(true);assert(get_fat(&fs,2)==UINT32_MAX&&nes_return_failed());cases++;
 setup(&fs);nes_return_io_begin();ticks=6000;assert(move_window(&fs,1)==FR_DISK_ERR&&!reads&&nes_return_failed());cases++;
 setup(&fs);nes_diag_leave();nes_return_fail(NES_DIAG_SPI);assert(get_fat(&fs,2)==2&&!reads);cases++;
 printf("PASS MENU065 FatFS cases=%u cached_FAT_budget=1 allocation_budget=1 inactive_legacy=1\n",cases);return 0;
}
