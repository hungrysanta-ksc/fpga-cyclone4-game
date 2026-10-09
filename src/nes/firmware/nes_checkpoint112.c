/* SPDX-License-Identifier: MIT */
#include <stdio.h>
#include <string.h>
#include "config.h"
#include "fileops.h"
#include "snes.h"
#include "nes_diag_runtime.h"
#include "nes_menu_return.h"
#include "nes_cf86_session094.h"
#include "nes_checkpoint112.h"

/* Foreground-only, at completed FatFS operations and idle FPGA CS boundaries.
 * Each append uses a new data sector. FAT metadata/SD power-loss atomicity is
 * not promised. A record names the NEXT operation unless bytes==total>0.
 * Never call this from observer/ISR/NMI or after the shared terminal latch. */
static bool enabled;
static uint32_t sequence,started,last_phase,last_bucket,last_total;
bool nes_checkpoint112(const char *stage,uint32_t bytes,uint32_t total) {
 FIL file;UINT written=0;char text[512];bool window=false;
 if(!enabled||nes_return_failed()||nes_cf86_failed094())return false;
 if(!nes_diag_active()||!get_snes_reset()||NVIC_GetEnableIRQ(OTG_FS_IRQn)||
    !nes_cf86_check094())goto fail;
 if(!nes_return_checkpoint_enter112())goto fail;
 window=true;
 int n=snprintf(text,sizeof(text),
  "NES112 seq=%lu stage=%s bytes=%lu total=%lu elapsed_ms=%lu next_or_progress=1\n",
  (unsigned long)sequence,stage,(unsigned long)bytes,(unsigned long)total,
  (unsigned long)((uint32_t)(nes_diag_ticks()-started)*10u));
 if(n<=0||n>510||sequence>=128)goto fail;
 memset(text+n,' ',sizeof(text)-(unsigned)n);text[511]='\n';
 if(f_open(&file,"/sd2snes/nes-progress-112.txt",
      FA_WRITE|(sequence?FA_OPEN_EXISTING:FA_CREATE_ALWAYS))!=FR_OK||nes_return_failed())goto fail;
 if(f_size(&file)!=sequence*512u)goto fail;
 if(f_lseek(&file,sequence*512u)!=FR_OK||nes_return_failed())goto fail;
 if(f_write(&file,text,sizeof(text),&written)!=FR_OK||written!=sizeof(text)||nes_return_failed())goto fail;
 if(f_sync(&file)!=FR_OK||nes_return_failed())goto fail;
 if(f_close(&file)!=FR_OK||nes_return_failed())goto fail;
 nes_return_checkpoint_leave112();window=false;
 if(!nes_cf86_check094())goto fail;
 sequence++;return true;
fail:
 /* No close/retry on an uncertain write or fault. The caller's terminal
  * path holds RESET; untouched prior records are the available evidence. */
 if(window)nes_return_checkpoint_leave112();
 enabled=false;nes_return_fail(NES_DIAG_MENU);return false;
}
bool nes_checkpoint_begin112(void) {
 if(nes_return_failed()||nes_cf86_failed094())return false;
 enabled=true;sequence=0;started=nes_diag_ticks();
 last_phase=last_bucket=last_total=UINT32_MAX;
 return nes_checkpoint112("OPEN_INPUT",0,0);
}
void nes_checkpoint_progress112(unsigned phase,uint32_t bytes,uint32_t total) {
 if(!enabled||nes_return_failed()||phase==NES_DIAG_BLOCKED)return;
 uint32_t bucket=bytes/16384u;
 if(phase==last_phase&&bucket==last_bucket&&total==last_total)return;
 const char *name=phase==NES_DIAG_VALIDATE?"VALIDATE":phase==NES_DIAG_CONFIG?"CONFIG_START":
  phase==NES_DIAG_LOAD?"LOAD":phase==NES_DIAG_CHECK?"CHECK":
  phase==NES_DIAG_RECOVER?(total?"MENU_COPY":"BASE_START"):"UNKNOWN";
 if(nes_checkpoint112(name,bytes,total)){last_phase=phase;last_bucket=bucket;last_total=total;}
}
