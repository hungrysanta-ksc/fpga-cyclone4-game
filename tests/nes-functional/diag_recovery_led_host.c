/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include "nes_diag_runtime.h"
int led_pwmstate,led_rdyledstate,led_readledstate,led_writeledstate;
static unsigned tick,reset,irq=1;
unsigned getticks(void){return tick;}
void rdyled(unsigned s){led_rdyledstate=s;}
void readled(unsigned s){led_readledstate=s;}
void writeled(unsigned s){led_writeledstate=s;}
void led_pwm(void){led_pwmstate=1;}
void led_std(void){led_pwmstate=0;}
void NVIC_DisableIRQ(unsigned n){assert(n==67);irq=0;}
void snes_reset(unsigned s){reset=s;}
int main(void){
 unsigned cases=0;
 for(unsigned pwm=0;pwm<2;pwm++)for(unsigned states=0;states<8;states++){
  led_pwmstate=pwm;rdyled(states&1);readled((states>>1)&1);writeled((states>>2)&1);
  tick=0;nes_diag_begin();assert(!led_pwmstate&&led_rdyledstate&&!led_readledstate&&!led_writeledstate);
  tick=25;nes_diag_led_tick();assert(led_readledstate&&!led_writeledstate);
  nes_diag_progress(NES_DIAG_LOAD,256,81920);assert(led_writeledstate&&!led_readledstate);
  nes_diag_progress(NES_DIAG_CHECK,256,81920);assert(led_readledstate&&!led_writeledstate);
  nes_diag_progress(NES_DIAG_RECOVER,0,0);assert(led_rdyledstate&&led_readledstate&&led_writeledstate);
  nes_diag_progress(NES_DIAG_BLOCKED,0,0);tick=50;nes_diag_led_tick();assert(!led_rdyledstate&&led_writeledstate&&!led_readledstate);
  nes_diag_leave();assert(led_pwmstate==(int)pwm&&led_rdyledstate==(int)(states&1)&&led_readledstate==(int)((states>>1)&1)&&led_writeledstate==(int)((states>>2)&1));
  nes_diag_led_tick();assert(led_rdyledstate==(int)(states&1));cases++;
 }
 assert(!reset&&irq);printf("PASS RECOVERY064 LED restoration_cases=%u reset_usb_unchanged=1\n",cases);return 0;
}
