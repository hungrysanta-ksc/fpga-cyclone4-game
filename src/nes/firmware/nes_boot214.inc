/* SPDX-License-Identifier: MIT */
#include "nes_boot214.h"
static uint32_t boot214_status(void){
 return (uint32_t)nes_run136.screen_stage|((uint32_t)nes_run136.screen_error<<8)|
  ((uint32_t)nes_run136.screen_flags<<16)|((uint32_t)nes_run136.screen_valid<<24);
}
static uint32_t boot214_signals(void){
 return (get_snes_reset()?1u:0u)|(fpga_get_done()?2u:0u)|
  (BITBAND(FPGA_MCU_RDY_REG->GPIO_I,FPGA_MCU_RDY_BIT)?4u:0u);
}
static bool native_boot172(const struct nes_rom_spi_io *io) __attribute__((noinline));
static bool native_boot172(const struct nes_rom_spi_io *io){
 uint32_t started=getticks();
 nes_boot214=(struct nes_boot214){0};nes_boot214.signals=boot214_signals();
 for(unsigned polls=0;polls<65536u;polls++){
  nes_boot214.polls=polls+1;
  if(!native_service165(NULL)){nes_boot214.reason=NES_BOOT214_SERVICE;break;}
  if(!screen146(io)){nes_boot214.reason=NES_BOOT214_STATUS;break;}
  nes_boot214.last=boot214_status();if(polls==0)nes_boot214.first=nes_boot214.last;
  if(nes_run136.screen_stage==3){nes_boot214.reason=NES_BOOT214_READY;break;}
  if(nes_run136.screen_stage==0xe1){nes_boot214.reason=NES_BOOT214_COPY;break;}
  if((uint32_t)(getticks()-started)>=500u){nes_boot214.reason=NES_BOOT214_TIMEOUT;break;}
 }
 if(!nes_boot214.reason)nes_boot214.reason=NES_BOOT214_POLL_LIMIT;
 nes_boot214.ticks=(uint32_t)(getticks()-started);
 nes_boot214.last=boot214_status();nes_boot214.signals|=boot214_signals()<<8;
 if(nes_boot214.reason==NES_BOOT214_READY)return true;
 native_runtime165.result=NES_RUNTIME165_SERVICE;
 if(!nes_run136.first_error)nes_run136.first_error=6;
 return false;
}
