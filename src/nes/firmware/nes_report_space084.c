/* SPDX-License-Identifier: GPL-2.0-only */
#include "config.h"
#include "ff.h"
#include "snes.h"
#include "nes_menu_return.h"
extern FATFS fatfs;
extern DWORD get_fat(FATFS *fs,DWORD cluster);
extern int sd_offload,ff_sd_offload,during_blocktrans;

/* Report-only eligibility scan, before CREATE_NEW and write permission.
 * No reservation, FAT update, free-count fabrication or deadline restart.
 * A short contiguous extent avoids an unbounded allocation search inside
 * the existing 10-second/10000-poll writer. Keep one spare cluster, but this
 * is NOT a root-directory reservation: its growth can replace last_clust
 * and still hit the bounded writer limit. Fragmented space may be rejected. */
bool report_space084(unsigned bytes) {
 if(nes_return_failed())return false;
 if(!nes_diag_active()||nes_return_log_allowed()||!get_snes_reset()||
    sd_offload||ff_sd_offload||during_blocktrans||
    (NVIC->ISER[OTG_FS_IRQn>>5]&(1u<<(OTG_FS_IRQn&31)))||
    fatfs.fs_type<FS_FAT12||fatfs.fs_type>FS_FAT32||
    !fatfs.csize||(fatfs.csize&(fatfs.csize-1))||fatfs.n_fatent<3||
    !bytes||bytes>3072)goto fail;
 unsigned need=(bytes-1)/(512u*fatfs.csize)+2,run=0;
 DWORD first=0,cluster=fatfs.last_clust;
 if(cluster<1||cluster>=fatfs.n_fatent-1)cluster=1;
 for(DWORD count=0;count<fatfs.n_fatent-2;count++) {
  if(++cluster>=fatfs.n_fatent){cluster=2;run=0;}
  DWORD value=get_fat(&fatfs,cluster);
  if(nes_return_failed()||value==0xffffffffu||value==1)goto fail;
  if(value){run=0;continue;}
  if(!run)first=cluster;
  if(++run==need){
   if(!nes_return_io_step())return false;
   fatfs.last_clust=first-1; /* publish only after the complete read check */
   return true;
  }
 }
fail:
 nes_return_fail(NES_DIAG_MENU);return false;
}
