/* SPDX-License-Identifier: GPL-2.0-only */
#include <string.h>
#include "config.h"
#include "snes.h"
#include "memory.h"
#include "nes_menu_return.h"
#include "nes_sd_fault074.h"
#include "nes_report_checkpoint079.h"

extern int snes_boot_configured, sd_offload, ff_sd_offload, during_blocktrans;
static const char *const labels[] = {
 "STEP 2 CREATE TXT", "STEP 3 WRITE CONTENT", "STEP 4 SYNC",
 "STEP 5 CLOSE WRITE", "STEP 6 OPEN READ", "STEP 7 VERIFY BYTES",
 "STEP 8 CLOSE READ"
};

void sdinv_checkpoint079(unsigned stage) {
 char line[33], back[33];
 /* No shared-SPI access after a fault, including a later close checkpoint.
  * RESET assertion alone is safe and is repeated on every exit. */
 if(nes_return_failed()) { snes_reset(1); return; }
 if(!nes_diag_active() || !nes_return_log_allowed() || stage<2 || stage>8 ||
    !snes_boot_configured || sd_offload || ff_sd_offload || during_blocktrans ||
    (NVIC->ISER[(unsigned)OTG_FS_IRQn>>5] & (1u<<((unsigned)OTG_FS_IRQn&31))) ||
    !get_snes_reset()) goto fail;
 sdinv_fault_stage(stage);
 if(!nes_return_io_step()) goto fail;
 memset(line,' ',32); line[32]=0;
 memcpy(line,labels[stage-2],strlen(labels[stage-2]));
 if(sram_writeblock(line,SRAM_CMD_ADDR+33u*8u,33)!=33 || nes_return_failed()) goto fail;
 if(sram_readblock(back,SRAM_CMD_ADDR+33u*8u,33)!=33 || nes_return_failed() ||
    memcmp(line,back,33) || !nes_return_io_step()) goto fail;
 /* The mini restarts its PPU/font/WRAM setup on every RESET release.
  * This is a bounded opportunity to render, not a display-consumption ACK.
  * Keep the existing report deadline running; never reopen the permission. */
 snes_reset(0);
 if(!nes_return_delay(500,true) || get_snes_reset()) goto fail;
 snes_reset(1);
 if(!get_snes_reset() || !nes_return_io_step()) goto fail;
 return;
fail:
 snes_reset(1);
 nes_return_fail(NES_DIAG_MENU); /* preserves the first shared fault */
}
