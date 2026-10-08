/* SPDX-License-Identifier: MIT */
/* MMIO effects for the real terminal body in the existing full main harness. */
static struct {uint32_t APB2RSTR;} rcc102;
#define RCC (&rcc102)
static unsigned barriers102,steps102,terminal102;
static void init102(void){
 mock_a.MODER=(mock_a.MODER&~(3u<<8))|(1u<<8);
 mock_a.ODR=(mock_a.ODR|16u)&~1u;
 mock_b.MODER=(mock_b.MODER&~((3u<<6)|(3u<<8)|(3u<<10)))|(2u<<6)|(2u<<8)|(2u<<10);
 mock_b.ODR|=40;mock_b.OTYPER=40;mock_a.OTYPER|=16;
 mock_spi.CR1=SPI_CR1_SPE;mock_spi.CR2=0xe3;rcc102.APB2RSTR=0x4002;
 barriers102=steps102=terminal102=0;
}
static void step102(unsigned line){
 (void)line;steps102++;
 MockGPIO *pins[]={GPIOA,GPIOB};
 for(unsigned i=0;i<2;i++){MockGPIO *g=pins[i];g->ODR=(g->ODR&~(g->BSRR>>16))|(g->BSRR&65535);g->BSRR=0;}
 if((mock_a.ODR&16)&&!cs100)cs_pin100(GPIOA,4,true);
 if(rcc102.APB2RSTR&RCC_APB2RSTR_SPI1RST){mock_spi.CR1=mock_spi.CR2=0;pending_rx100=0;}
 assert(steps102<=15);
}
static void check_quiesce102(void){
 assert(cs100&&(mock_a.ODR&16)&&((mock_a.MODER>>8)&3)==1);
 assert(((mock_b.MODER>>6)&3)==1&&((mock_b.MODER>>10)&3)==1&&((mock_b.MODER>>8)&3)==0);
 assert(!(mock_b.ODR&40)&&!(mock_b.OTYPER&40)&&!(mock_a.OTYPER&16));
 assert(!mock_spi.CR1&&!mock_spi.CR2&&rcc102.APB2RSTR==0x5002);
 assert(barriers102==3&&steps102==15&&!irq&&reset_held&&(mock_a.MODER&3)==1);
}
#define __DSB() (++barriers102)
#undef SET_BIT
#undef CLEAR_BIT
#include "gpio102.h"
#include "snes102.inc"
#include "quiesce102.inc"
#undef __NOP
#define __NOP() do {check_quiesce102();terminal102++;blocked098++;longjmp(blocked_env098,1);} while(0)
#include "blocked102.inc"
#undef __NOP
#define __NOP() ((void)0)
