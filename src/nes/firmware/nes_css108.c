/* SPDX-License-Identifier: MIT */
#include "config.h"
#include "nes_css108.h"
#include "nes_diag_runtime.h"
#include "nes_menu_return.h"

/* Host seams observe the same volatile register expressions. Production uses
 * direct MMIO, without callback, timer, formatter, or filesystem dependencies. */
#ifndef CSS108_READ
#define CSS108_READ(reg) (reg)
#endif
#ifndef CSS108_WRITE
#define CSS108_WRITE(reg,value) ((reg)=(value))
#endif
static volatile uint32_t owned108,claimed108,fault108;
uint32_t nes_css_fault108(void){return fault108;}

static void stop108(uint32_t reason) __attribute__((noreturn,noinline));
static void stop108(uint32_t reason) {
 __disable_irq();
 if(!fault108)fault108=reason;
 /* GPIO A/B clocks and PA0/PA1 ownership were checked before claiming CSS.
  * Preserve RESET output type; stock code asserts by direction, releases by
  * input mode. Preload LOW before output mode, never drive RESET HIGH. */
 CSS108_WRITE(GPIOA->BSRR,1u<<16);
 CSS108_WRITE(GPIOA->MODER,(CSS108_READ(GPIOA->MODER)&~3u)|1u);
 NVIC_DisableIRQ(OTG_FS_IRQn);
 CSS108_WRITE(GPIOA->BSRR,1u<<17); /* nCONFIG LOW; configuration is lost */
 __DSB();
 CSS108_WRITE(GPIOA->BSRR,1u<<4);  /* CS HIGH before SPI GPIO mux changes */
 CSS108_WRITE(GPIOA->OTYPER,CSS108_READ(GPIOA->OTYPER)&~(1u<<4));
 CSS108_WRITE(GPIOA->MODER,(CSS108_READ(GPIOA->MODER)&~(3u<<8))|(1u<<8));
 CSS108_WRITE(GPIOB->BSRR,((1u<<3)|(1u<<5))<<16);
 CSS108_WRITE(GPIOB->OTYPER,CSS108_READ(GPIOB->OTYPER)&~((1u<<3)|(1u<<5)));
 CSS108_WRITE(GPIOB->MODER,(CSS108_READ(GPIOB->MODER)&~((3u<<6)|(3u<<8)|(3u<<10)))|(1u<<6)|(1u<<10));
 CSS108_WRITE(SPI1->CR2,0);
 CSS108_WRITE(SPI1->CR1,CSS108_READ(SPI1->CR1)&~SPI_CR1_SPE);
 CSS108_WRITE(RCC->APB2RSTR,CSS108_READ(RCC->APB2RSTR)|RCC_APB2RSTR_SPI1RST);
 /* W1C CSSF; preserving RCC interrupt enables, not echoing other W1C bits. */
 CSS108_WRITE(RCC->CIR,(CSS108_READ(RCC->CIR)&0x00007f00u)|RCC_CIR_CSSC);
 __DSB();__ISB();
 for(;;)__NOP(); /* Never exception-return into HSE-clocked foreground code. */
}

void NMI_Handler(void) {
 uint32_t css=CSS108_READ(RCC->CIR)&RCC_CIR_CSSF;
 /* claimed remains sticky for an already-pending CSS NMI at disarm. Before
  * the first diagnostic claim, retain the legacy unhandled-NMI loop. */
 if(owned108||(claimed108&&css))stop108(css?1u:2u);
 for(;;)__NOP();
}

bool nes_css_begin108(void) {
 if(fault108||owned108||!nes_diag_active()||nes_return_failed())return false;
 if(NVIC_GetEnableIRQ(OTG_FS_IRQn))return false;
 if((CSS108_READ(RCC->AHB1ENR)&3u)!=3u)return false;
 if((CSS108_READ(GPIOA->MODER)&15u)!=5u ||
    (CSS108_READ(GPIOA->ODR)&1u))return false;
 uint32_t cr=CSS108_READ(RCC->CR);
 /* Do not take over pre-enabled CSS, or silently clear a pending failure. */
 if((cr&RCC_CR_CSSON)||(CSS108_READ(RCC->CIR)&RCC_CIR_CSSF))return false;
 if((cr&(RCC_CR_HSEON|RCC_CR_HSERDY|RCC_CR_PLLRDY))!=
    (RCC_CR_HSEON|RCC_CR_HSERDY|RCC_CR_PLLRDY))return false;
 if(!(CSS108_READ(RCC->PLLCFGR)&RCC_PLLCFGR_PLLSRC_HSE)||
    (CSS108_READ(RCC->CFGR)&RCC_CFGR_SWS)!=RCC_CFGR_SWS_PLL)return false;
 claimed108=owned108=1;
 __DMB();
 CSS108_WRITE(RCC->CR,CSS108_READ(RCC->CR)|RCC_CR_CSSON);
 __DSB();__ISB();
 if(!(CSS108_READ(RCC->CR)&RCC_CR_HSERDY)||(CSS108_READ(RCC->CIR)&RCC_CIR_CSSF))stop108(1);
 return true;
}

bool nes_css_end108(void) {
 if(fault108)return false;
 if(!owned108)return true;
 if(nes_return_failed())return false; /* leave protection armed on shared fault */
 if((CSS108_READ(RCC->CIR)&RCC_CIR_CSSF)||!(CSS108_READ(RCC->CR)&RCC_CR_HSERDY))stop108(1);
 CSS108_WRITE(RCC->CR,CSS108_READ(RCC->CR)&~RCC_CR_CSSON);
 __DSB();__ISB();
 if((CSS108_READ(RCC->CIR)&RCC_CIR_CSSF)||!(CSS108_READ(RCC->CR)&RCC_CR_HSERDY))stop108(1);
 owned108=0;
 __DMB();
 return true;
}
