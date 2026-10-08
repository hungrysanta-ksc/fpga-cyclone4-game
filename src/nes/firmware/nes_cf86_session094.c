/* SPDX-License-Identifier: MIT */
#include "config.h"
#include "bits.h"
#include "snes.h"
#include "fpga.h"
#include "nes_menu_return.h"
#include "nes_cf86_session094.h"
extern int sd_offload,ff_sd_offload,during_blocktrans;
extern int fpga_get_done(void);
enum phase094 {IDLE094,CONFIG094,ARMED094,FAILED094};
static enum phase094 phase094;

bool nes_cf86_failed094(void){return phase094==FAILED094;}
bool nes_cf86_monitoring094(void){return phase094==ARMED094;}
bool nes_cf86_fail094(void){
 phase094=FAILED094;
 NVIC_DisableIRQ(OTG_FS_IRQn);snes_reset(1);
 nes_return_fail(NES_DIAG_SPI);
 return false;
}
static bool owner094(void){
 return get_snes_reset()&&!NVIC_GetEnableIRQ(OTG_FS_IRQn)&&
  !sd_offload&&!ff_sd_offload&&!during_blocktrans&&!nes_return_log_allowed()&&!nes_return_failed();
}
bool nes_cf86_enter094(void){
 if(phase094!=IDLE094||!owner094())return nes_cf86_fail094();
 phase094=CONFIG094;return true;
}
bool nes_cf86_arm094(void){
 if(phase094!=CONFIG094||!nes_diag_active()||!owner094()||!fpga_get_done()||
    !BITBAND(FPGA_MCU_RDY_REG->GPIO_I,FPGA_MCU_RDY_BIT))return nes_cf86_fail094();
 phase094=ARMED094;return true;
}
bool nes_cf86_check094(void){
 if(phase094==FAILED094)return false;
 /* Legacy paths are unchanged when the CF86 session is not armed. */
 if(phase094!=ARMED094)return true;
 if(!nes_diag_active()||!owner094()||!fpga_get_done()||
    !BITBAND(FPGA_MCU_RDY_REG->GPIO_I,FPGA_MCU_RDY_BIT))return nes_cf86_fail094();
 return true;
}
bool nes_cf86_finish094(void){
 if(phase094==FAILED094)return false;
 if(phase094==ARMED094&&!nes_cf86_check094())return false;
 /* Called only after normal STOP, before intentional base reconfiguration,
  * or before FPGA changes on rejected input. It cannot clear FAILED. */
 phase094=IDLE094;return true;
}
