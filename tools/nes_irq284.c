/* SPDX-License-Identifier: MIT */
/* PB8 is the existing FPGA MCU_RDY pin. This diagnostic owner starts only
 * after the common E2 view selects progress mode. SPI stays in foreground;
 * the IRQ only acknowledges EXTI8. Other EXTI9_5 sources are not owned here.
 * Production RUN/NVIC integration remains a separate packaging gate. */
#include <stdint.h>
#define REG(a) (*(volatile uint32_t *)(a))
#define PIN (1u<<8)
volatile unsigned wakes284;
static unsigned active284;
void EXTI9_5_IRQHandler(void){
 if(REG(0x40013c14)&PIN){REG(0x40013c14)=PIN;wakes284++;}
}
void irq_init284(void){
 REG(0x40023830)|=2;REG(0x40023844)|=1u<<14;
 REG(0x40020400)&=~(3u<<16); /* PB8 input; SPI pins untouched. */
 REG(0x40013810)=(REG(0x40013810)&~15u)|1u;
 REG(0x40013c08)|=PIN;REG(0x40013c0c)&=~PIN;
 REG(0x40013c14)=PIN;REG(0x40013c00)&=~PIN;active284=0;
 REG(0xe000e100)=1u<<23;
}
void irq_begin284(void){
 /* Only after a checked E2 response switched the physical pin owner. */
 if(!active284){REG(0x40013c14)=PIN;REG(0x40013c00)|=PIN;active284=1;}
}
void irq_end284(void){
 /* Source memory-ready activity must not become progress interrupts. */
 REG(0x40013c00)&=~PIN;REG(0x40013c14)=PIN;active284=0;
}
void wait284(void){
 /* Mask/check/WFI/unmask closes the edge-before-sleep race. A pending EXTI
  * wakes WFI even with PRIMASK set. SysTick can cause a checked fallback. */
 __asm volatile("cpsid i" ::: "memory");
 if(!(REG(0x40020410)&PIN))__asm volatile("dsb\n wfi" ::: "memory");
 __asm volatile("cpsie i\n isb" ::: "memory");
}
