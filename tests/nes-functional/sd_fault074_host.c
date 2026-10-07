/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <setjmp.h>
#ifdef _WIN32
#include <windows.h>
#include <stdlib.h>
#endif
#include "nes_diag_runtime.h"
#include "nes_sd_fault074.h"
int led_pwmstate,led_rdyledstate,led_readledstate,led_writeledstate;
static uint32_t tick;
static unsigned reset,usb;
static jmp_buf stop;
uint32_t getticks(void){return tick;}
void rdyled(int n){led_rdyledstate=n;}
void readled(int n){led_readledstate=n;}
void writeled(int n){led_writeledstate=n;}
void led_std(void){led_pwmstate=0;}
void led_pwm(void){led_pwmstate=1;}
void snes_reset(int n){reset=n;}
void NVIC_DisableIRQ(unsigned n){assert(n==67);usb=1;}
void mock_halt(void){longjmp(stop,1);}
int main(void){
#ifdef _WIN32
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
 _set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);
#endif
 const unsigned errors[]={1,2,3,4,5,16,14,15,6};
 unsigned cases=0;
 for(unsigned wrap=0;wrap<2;wrap++)for(unsigned e=0;e<9;e++)for(unsigned stage=1;stage<=9;stage++){
  tick=wrap?UINT32_MAX-90u:100u;
  led_pwmstate=1;led_rdyledstate=0;led_readledstate=1;led_writeledstate=0;
  sdinv_fault_stage(stage);nes_diag_begin();
  nes_diag_fail((enum nes_diag_error)errors[e]);
  uint32_t start=tick;
  /* A later checkpoint, secondary error, and BLOCKED must not change cause. */
  sdinv_fault_stage(9);nes_diag_fail(NES_DIAG_SD_BUSY);
  reset=usb=0;if(!setjmp(stop))nes_diag_blocked();
  assert(reset&&usb&&nes_diag_active());
  unsigned nr=0,nw=0,previous_r=0,previous_w=0,period=800+100*(e+1+stage);
  for(unsigned t=0;t<period;t++){
   tick=start+t;nes_diag_led_tick();
   if(t<200){assert(led_rdyledstate&&led_readledstate&&led_writeledstate);continue;}
   assert(!led_rdyledstate);
   if(led_readledstate&&!previous_r)nr++;
   if(led_writeledstate&&!previous_w)nw++;
   assert(!(led_readledstate&&led_writeledstate));
   previous_r=led_readledstate;previous_w=led_writeledstate;
  }
  assert(nr==e+1&&nw==stage);
  tick=start+period;nes_diag_led_tick();assert(led_rdyledstate&&led_readledstate&&led_writeledstate);
  /* Stopped tick is visibly stationary; no fictitious timing guarantee. */
  for(unsigned n=0;n<5;n++)nes_diag_led_tick();
  assert(led_rdyledstate&&led_readledstate&&led_writeledstate);
  nes_diag_leave();assert(led_pwmstate&&!led_rdyledstate&&led_readledstate&&!led_writeledstate);
  cases++;
 }
 tick=0;sdinv_fault_stage(1);nes_diag_begin();assert(!led_rdyledstate&&!led_readledstate&&!led_writeledstate);
 tick=25;nes_diag_led_tick();assert(led_rdyledstate&&!led_readledstate&&!led_writeledstate);
 nes_diag_leave();
 printf("PASS074 LED cases=%u first_fault_frozen=1 tick_wrap=1 RESET_USB=1 no_UART_SPI_SD_symbols=1\n",cases);
 return 0;
}
