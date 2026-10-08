/* SPDX-License-Identifier: MIT */
/* Register/event model; no physical clock, ISR timing or pad-delay claim. */
#include "peripheral-registers104.h"
static MockGPIO mock_c;
#define GPIOC (&mock_c)
static struct {uint32_t SR,CNT,CR1,CCR1,CCR2,CCR3;} timer104,timled104;
#define TIM2 (&timer104)
#define TIM3 (&timled104)
volatile tick_t ticks;
volatile int reset_changed,reset_pressed;
extern volatile int sd_changed;
void sdn_changed(void);
unsigned card_detect104(void);
static unsigned in_irq104,irq_calls104,timer_polls104,timer_stall104,tick_freeze104;
static unsigned timer_harness_limit104=UINT32_MAX;
static unsigned timer_done104,timer_started104,cic_reads104,cic_transitions104,cic_previous104;
static unsigned cic_override104,cic_level104=1,cic_budget104;
static unsigned uart_target104,uart_count104,uart_irq104,inject_uart104;
static uint32_t timer_alias104,gpio_alias104;
static unsigned long long next_tick104=10000000ull;
static void service104(void);
static void wire_delay_us104(unsigned);
static void flush104(void){
 MockGPIO*g[]={GPIOA,GPIOB,GPIOC};
 for(unsigned i=0;i<3;i++){g[i]->ODR=(g[i]->ODR&~(g[i]->BSRR>>16))|(g[i]->BSRR&65535);g[i]->BSRR=0;}
}
static uint32_t *bit104(uint32_t *reg,unsigned bit){
 if(reg==&TIM2->SR){
  if(!TIM2->CR1){timer_done104=0;timer_alias104=0;}
  else {
   timer_polls104++;assert(timer_polls104<timer_harness_limit104);
   if(!timer_done104&&!timer_stall104){
    timer_started104++;timer_done104=1;
    wire_delay_us104(TIM2->CNT/(CONFIG_CPU_FREQUENCY/1000000u));service104();timer_alias104=1;
   }
  }
  return &timer_alias104;
 }
 if(reg==&GPIOC->IDR&&bit==SNES_CIC_STATUS_BIT){
  unsigned at=cic_reads104++%(CIC_SAMPLECOUNT+1u);
  unsigned budget=cic_override104?cic_budget104:(scenario098==2?2000u:scenario098==3?100u:0u);
  unsigned high=cic_override104?cic_level104:!((scenario098==4&&!menu_enter098)||(scenario098==8&&release097));
  gpio_alias104=high^(budget?((at<=budget?at:budget)&1u):0u);
  return &gpio_alias104;
 }
 gpio_alias104=(*reg>>bit)&1u;return &gpio_alias104;
}
#undef BITBAND
#define BITBAND(r,b) (*bit104(&(r),(b)))
#undef OUT_BIT
#define OUT_BIT(r,b,v) do {r->BSRR=((0x00010000u<<(b))|((v)<<(b)));flush104();}while(0)
/* Bit-band OTYPER alias write modeled directly; original macro is archived. */
#undef GPIO_OPENDRAIN
#define GPIO_OPENDRAIN(r,b) ((r)->OTYPER|=1u<<(b))
#undef led_pwm
int led_pwmstate,led_rdyledstate,led_readledstate,led_writeledstate;
#include "led104.inc"
#include "reset104.inc"
#include "cic104.inc"
#include "timer104.inc"
#define SDCARD_DETECT card_detect104()
#define WARMUP_TICKS 15
#include "systick104.inc"
static void service104(void){
 if(in_irq104||tick_freeze104)return;
 while(ns+native_ns096>=next_tick104){
  next_tick104+=10000000ull;in_irq104=1;SysTick_Handler();in_irq104=0;irq_calls104++;
 }
}
static void uart_preempt104(void){
 if(in_irq104){uart_irq104++;assert(!"diagnostic SysTick reentered UART/formatter");}
 if(inject_uart104&&uart_count104++==uart_target104){
  sd_changed=1;in_irq104=1;SysTick_Handler();in_irq104=0;irq_calls104++;
 }
}
