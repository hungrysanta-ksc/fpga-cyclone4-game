/* SPDX-License-Identifier: MIT */
/* Screen138-only materialization of the094 session. Legacy094 is unchanged. */
#include "config.h"
#include "bits.h"
#include "snes.h"
#include "fpga.h"
#include "nes_menu_return.h"
#include "nes_cf86_session094.h"
extern int sd_offload,ff_sd_offload,during_blocktrans;
extern int fpga_get_done(void);
enum phase094 {IDLE094,CONFIG094,ARMED094,RELEASING138,DISPLAY138,FAILED094};
static enum phase094 phase094;
bool nes_cf86_failed094(void){return phase094==FAILED094;}
bool nes_cf86_monitoring094(void){return phase094==ARMED094||phase094==RELEASING138||phase094==DISPLAY138;}
bool nes_cf86_fail094(void){
 phase094=FAILED094;
 NVIC_DisableIRQ(OTG_FS_IRQn);snes_reset(1);
 nes_return_fail(NES_DIAG_SPI);return false;
}
static bool owner094(void){
 bool reset_ok=phase094==RELEASING138 || (phase094==DISPLAY138 ? !get_snes_reset() : get_snes_reset());
 return reset_ok&&!NVIC_GetEnableIRQ(OTG_FS_IRQn)&&!sd_offload&&!ff_sd_offload&&
  !during_blocktrans&&!nes_return_log_allowed()&&!nes_return_failed();
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
 if(!nes_cf86_monitoring094())return true;
 if(!nes_diag_active()||!owner094()||!fpga_get_done()||
    !BITBAND(FPGA_MCU_RDY_REG->GPIO_I,FPGA_MCU_RDY_BIT))return nes_cf86_fail094();
 return true;
}
bool nes_display_enter138(void){
 if(phase094!=ARMED094||!nes_cf86_check094())return nes_cf86_fail094();
 /* Only this bounded settling interval accepts either RESET sense level.
  * CSS/NMI, shared faults, DONE/RDY and exclusive ownership remain active. */
 phase094=RELEASING138;snes_reset(0);
 if(!nes_return_delay(1,true)||!nes_cf86_check094())return nes_cf86_fail094();
 phase094=DISPLAY138;return nes_cf86_check094();
}
bool nes_display_leave138(void){
 if(phase094!=DISPLAY138||!nes_cf86_check094())return nes_cf86_fail094();
 /* Assert first; never issue STOP or filesystem IO with the SNES running. */
 snes_reset(1);phase094=ARMED094;return nes_cf86_check094();
}
bool nes_cf86_finish094(void){
 if(phase094==FAILED094)return false;
 if(phase094==DISPLAY138||phase094==RELEASING138)return nes_cf86_fail094();
 if(phase094==ARMED094&&!nes_cf86_check094())return false;
 phase094=IDLE094;return true;
}
