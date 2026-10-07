/* SPDX-License-Identifier: MIT */
#include <stdio.h>
#include "config.h"
#include "timer.h"
#include "led.h"
#include "snes.h"
#include "nes_diag_runtime.h"
/* Only these two aligned scalars are shared with SysTick. The multi-field
 * report is owned by the foreground diagnostic, never read by the ISR. */
static volatile unsigned led_phase,led_owned;
extern int led_pwmstate,led_rdyledstate,led_readledstate,led_writeledstate;
static int saved_pwm,saved_ready,saved_read,saved_write;
static unsigned previous_phase,previous_error,previous_quarter;
uint32_t nes_diag_ticks(void){return getticks();}
void nes_diag_led_tick(void) {
 if(!led_owned)return;
 unsigned phase=led_phase,blink=(getticks()/25u)&1u;
 rdyled(phase==NES_DIAG_BLOCKED ? blink : 1);
 readled((phase==NES_DIAG_VALIDATE||phase==NES_DIAG_CHECK) ? blink : phase==NES_DIAG_RECOVER);
 writeled((phase==NES_DIAG_LOAD||phase==NES_DIAG_CONFIG) ? blink : phase==NES_DIAG_BLOCKED||phase==NES_DIAG_RECOVER);
}
void nes_diag_observe(const struct nes_diag_report *r,bool active) {
 if(active&&!led_owned){
  saved_pwm=led_pwmstate;saved_ready=led_rdyledstate;saved_read=led_readledstate;saved_write=led_writeledstate;
  previous_phase=previous_error=previous_quarter=UINT32_MAX;
  led_std();led_phase=r->phase;led_owned=1;
 }
 if(!active&&led_owned){
  led_owned=0;if(saved_pwm)led_pwm();else led_std();
  rdyled(saved_ready);readled(saved_read);writeled(saved_write);return;
 }
 if(!active)return;
 led_phase=r->phase;nes_diag_led_tick();
 unsigned quarter=r->total?(unsigned)(((uint64_t)r->completed*4u)/r->total):0;
 if(previous_phase!=(unsigned)r->phase||previous_error!=(unsigned)r->error||previous_quarter!=quarter){
  previous_phase=r->phase;previous_error=r->error;previous_quarter=quarter;
  printf("NES064 phase=%u error=%u progress=%lu/%lu\n",(unsigned)r->phase,(unsigned)r->error,
   (unsigned long)r->completed,(unsigned long)r->total);
 }
}
void nes_diag_blocked(void) {
 NVIC_DisableIRQ(OTG_FS_IRQn);snes_reset(1);
 if(!nes_diag_active())nes_diag_begin();
 nes_diag_progress(NES_DIAG_BLOCKED,0,0);
 /* Deliberate fail-closed state. No CLI, SD, USB, retries or RESET release.
  * External power/reset intervention remains necessary; not pad cancellation. */
 for(;;)__NOP();
}
