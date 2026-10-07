/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual077 timer/runtime/return code, modeled TIM2 and100Hz clock. */
#include <assert.h>
#include <stdio.h>
#include "nes_menu_return.h"
static struct {uint32_t SR,CNT,CR1;} tim;
static unsigned calls,complete_after,tick_every,origin;
#define TIM2 (&tim)
#define CONFIG_CPU_FREQUENCY 84000000u
#define TIM_SR_UIF_Pos 0
#define TIM_CR1_URS 4u
#define TIM_CR1_DIR 16u
#define TIM_CR1_CEN 1u
static uint32_t *timer_bit(void){calls++;if(complete_after&&calls>=complete_after)tim.SR=1;return &tim.SR;}
#define BITBAND(r,p) (*timer_bit())
uint32_t nes_diag_ticks(void){return origin+(tick_every?calls/tick_every:0);}
bool nes_diag_sd_failed(void){return false;}
void nes_diag_observe(const struct nes_diag_report *r,bool a){(void)r;(void)a;}
#include "timer.inc"
static void reset(void){nes_diag_leave();nes_return_reset();nes_diag_begin();calls=complete_after=tick_every=origin=0;tim.SR=tim.CNT=tim.CR1=0;}
int main(void){
 reset();complete_after=100;assert(nes_return_delay(500,true));
 assert(tim.CNT==42000000&&tim.CR1==0&&tim.SR==0&&!nes_return_failed());
 reset();assert(!nes_return_delay(500,true));
 assert(calls>=42100000&&calls<42100010&&tim.CR1==0&&nes_diag_status()->error==NES_DIAG_TIMER);
 reset();origin=UINT32_MAX-10;tick_every=1;assert(!nes_return_delay(500,true));
 assert(calls>=52&&calls<60&&tim.CR1==0&&nes_diag_status()->error==NES_DIAG_TIMER);
 reset();assert(!nes_return_delay(UINT32_MAX,true)&&!calls&&nes_return_failed());
 reset();nes_return_fail(NES_DIAG_SPI);assert(!nes_return_delay(500,true)&&!calls&&nes_diag_status()->error==NES_DIAG_SPI);
 puts("PASS079 TIMER checks=5 physical=0");return 0;
}
