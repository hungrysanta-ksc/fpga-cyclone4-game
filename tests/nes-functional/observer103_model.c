/* SPDX-License-Identifier: MIT */
/* Register effects only. A stalled CPU/APB and pad propagation are not modeled. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#include "nes_diag_runtime.h"
typedef struct {unsigned MODER,OTYPER,ODR,BSRR;} GPIO103;
static GPIO103 ga,gb;
static struct {unsigned CR1,CR2,SR,DR;} spi;
static struct {unsigned APB2RSTR;} rcc;
#define GPIOA (&ga)
#define GPIOB (&gb)
#define SPI1 (&spi)
#define RCC (&rcc)
#include "registers.h"
static unsigned irq=1,steps,barriers,phase_started,shared,sd_fault;
static unsigned uart_reads,uart_writes,clock_reads,led_calls,ready=1,ticking;
static unsigned ticks103,uart_dr,uart_dropped_at_fault,first_clock,first_uart,first_led;
volatile uint32_t nes_diag_uart_dropped;
static jmp_buf env;
static void check_isolated(void){
 assert((ga.ODR&16)&&((ga.MODER>>8)&3)==1&&(ga.MODER&3)==1);
 assert(((gb.MODER>>6)&3)==1&&((gb.MODER>>10)&3)==1&&((gb.MODER>>8)&3)==0);
 assert(!(gb.ODR&40)&&!spi.CR1&&!spi.CR2&&(rcc.APB2RSTR&4096)&&!irq);
}
static void step102(unsigned n){
 (void)n;steps++;
 GPIO103 *g[]={GPIOA,GPIOB};
 for(unsigned i=0;i<2;i++){g[i]->ODR=(g[i]->ODR&~(g[i]->BSRR>>16))|(g[i]->BSRR&65535);g[i]->BSRR=0;}
 if(rcc.APB2RSTR&4096)spi.CR1=spi.CR2=0;
}
#define __DSB() (++barriers)
#define OTG_FS_IRQn 67
#define NVIC_DisableIRQ(n) do {assert((n)==67);irq=0;}while(0)
#define __NOP() do {check_isolated();longjmp(env,1);}while(0)
static uint32_t getticks(void){clock_reads++;ticks103+=ticking;return ticks103;}
int led_pwmstate,led_rdyledstate,led_readledstate,led_writeledstate;
static void led_std(void){led_calls++;led_pwmstate=0;}
static void led_pwm(void){led_calls++;led_pwmstate=1;}
static void rdyled(unsigned v){led_calls++;led_rdyledstate=v;}
static void readled(unsigned v){led_calls++;led_readledstate=v;}
static void writeled(unsigned v){led_calls++;led_writeledstate=v;}
static unsigned txe103(void){
 uart_reads++;
 /* Exposes the old first-fault -> observer UART gap with a finite assertion. */
 if(phase_started&&(shared||sd_fault))check_isolated();
 assert(uart_reads<20000000u);return ready;
}
#define USART_SR_TXE_Pos 7
#define BITBAND(reg,bit) txe103()
static struct {unsigned SR,DR;} uart;
#define UART_REGS (&uart)
bool nes_diag_sd_failed(void){return sd_fault;}
#include "shared.inc"
#include "reset.inc"
#include "quiesce.inc"
#include "uart.inc"
int diag_printf(const char *,...);
#define printf diag_printf
#include "observer.inc"
#include "blocked.inc"
#undef printf
static void mark_fault(void){phase_started=1;first_clock=clock_reads;first_uart=uart_reads;first_led=led_calls;uart_dropped_at_fault=nes_diag_uart_dropped;}
int main(int argc,char **argv){
 assert(argc==2);unsigned mode=(unsigned)atoi(argv[1]);setvbuf(stdout,NULL,_IONBF,0);
 ga=(GPIO103){.MODER=0xaaaaaaaa,.ODR=0,.OTYPER=0xffff};gb=(GPIO103){.MODER=0xaaaaaaaa,.ODR=40,.OTYPER=0xffff};
 spi.CR1=64;spi.CR2=0xe3;uart.DR=0x1234;
 nes_diag_begin();assert(!steps&&uart_reads&&uart.DR=='\n');
 ready=!(mode&1);ticking=(mode>>1)&1;
 if(mode<4){
  /* A report-only error must preserve the recovery path, including UART. */
  unsigned before=uart_reads;nes_diag_fail(NES_DIAG_FPGA_OPEN);
  assert(!steps&&!nes_return_failed()&&uart_reads>before);
  unsigned stable=uart_reads;nes_diag_fail(NES_DIAG_FPGA_OPEN);assert(uart_reads==stable);
  if(!ready)assert(nes_diag_uart_dropped>0);
  nes_diag_leave();assert(!nes_diag_active()&&!steps);
 }else if(mode<12){
  mark_fault();
  if(mode&4)nes_return_fail(NES_DIAG_SPI);else nes_diag_sd_error(NES_DIAG_SD_CRC);
  check_isolated();assert(steps==15&&barriers==3);
  assert(clock_reads==first_clock&&uart_reads==first_uart&&led_calls==first_led);
  unsigned error=nes_diag_status()->error;uart_dr=uart.DR;
  uart_putc('\n');uart_flush();diag_printf("late %u\n",123u);
  assert(uart.DR==uart_dr&&uart_reads==first_uart&&clock_reads==first_clock);
  assert(nes_diag_uart_dropped>uart_dropped_at_fault);
  if(!setjmp(env))nes_diag_blocked();
  assert(nes_diag_status()->error==error&&nes_diag_active());check_isolated();
 }else if(mode<16){
  /* Existing per-character bounds terminate even when SysTick is frozen. */
  unsigned before=uart_reads;uart_putc('\n');uart_flush();
  assert(uart_reads>before&&!steps&&!nes_return_failed());
  if(!ready)assert(nes_diag_uart_dropped>=3);
 }else{
  nes_diag_leave();shared=sd_fault=1;ready=1;mark_fault();phase_started=0;
  nes_diag_fail(NES_DIAG_SPI);assert(!steps);uart_putc('L');assert(uart.DR=='L');
 }
 printf("PASS103 mode=%u steps=%u barriers=%u uart_reads=%u ticks=%u dropped=%u\n",mode,steps,barriers,uart_reads,clock_reads,(unsigned)nes_diag_uart_dropped);
 return 0;
}
