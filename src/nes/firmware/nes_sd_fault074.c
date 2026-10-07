/* SPDX-License-Identifier: MIT */
/* SDINFO074 only: replaces nes_diag_platform.c in a separate build.
 * Error display uses MCU LEDs only, never UART/SPI/SD or RESET release. */
#include "config.h"
#include "timer.h"
#include "led.h"
#include "snes.h"
#include "nes_diag_runtime.h"
#include "nes_sd_fault074.h"
extern int led_pwmstate,led_rdyledstate,led_readledstate,led_writeledstate;
static int saved_pwm,saved_ready,saved_read,saved_write;
/* Aligned single-word ISR snapshots. Foreground is the only writer. */
static volatile unsigned owned,stage=1,signal;
static volatile uint32_t epoch;
static unsigned error_code(unsigned error){
 if(error>=1&&error<=5)return error;
 if(error==16)return 6; /* bounded filesystem/menu budget */
 if(error==14)return 7; /* shared SPI */
 if(error==15)return 8; /* timer */
 return 9; /* no recorded cause / other */
}
void sdinv_fault_stage(unsigned value){if(!signal)stage=value>=1&&value<=9?value:9;}
uint32_t nes_diag_ticks(void){return getticks();}
void nes_diag_led_tick(void){
 if(!owned)return;
 unsigned code=signal;
 uint32_t ticks=getticks();
 if(!code){rdyled((ticks/25u)&1u);readled(0);writeled(0);return;}
 unsigned error=code&15u,at=(code>>4)&15u;
 /* 100 Hz: all three 2 s, dark 1 s, READ error pulses, dark 2 s,
  * WRITE stage pulses, dark 3 s. Each pulse is 0.5 s on / 0.5 s off. */
 unsigned t=(uint32_t)(ticks-epoch)%(800u+100u*(error+at));
 if(t<200u){rdyled(1);readled(1);writeled(1);return;}
 rdyled(0);readled(0);writeled(0);
 if(t>=300u&&t<300u+100u*error)readled((t-300u)%100u<50u);
 unsigned start=500u+100u*error;
 if(t>=start&&t<start+100u*at)writeled((t-start)%100u<50u);
}
void nes_diag_observe(const struct nes_diag_report *r,bool active){
 if(active&&!owned){
  saved_pwm=led_pwmstate;saved_ready=led_rdyledstate;saved_read=led_readledstate;saved_write=led_writeledstate;
  led_std();signal=0;owned=1;
 }
 if(!active&&owned){
  owned=0;signal=0;if(saved_pwm)led_pwm();else led_std();
  rdyled(saved_ready);readled(saved_read);writeled(saved_write);return;
 }
 if(!active)return;
 if(!signal&&(r->error||r->phase==NES_DIAG_BLOCKED)){
  epoch=getticks(); /* publish epoch before atomic signal */
  signal=(stage<<4)|error_code((unsigned)r->error);
 }
 nes_diag_led_tick();
}
void nes_diag_blocked(void){
 NVIC_DisableIRQ(OTG_FS_IRQn);snes_reset(1);
 if(!nes_diag_active())nes_diag_begin();
 nes_diag_progress(NES_DIAG_BLOCKED,0,0);
 /* SysTick normally drives the LEDs. Polling is redundant if interrupts are
  * disabled but does NOT claim a working timebase when SysTick has stopped. */
 for(;;){nes_diag_led_tick();__NOP();}
}
