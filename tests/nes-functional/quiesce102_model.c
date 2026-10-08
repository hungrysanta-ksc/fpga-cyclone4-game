/* SPDX-License-Identifier: MIT */
/* Ordered MMIO/register model. No analog delay, CPU time or FPGA rollback. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#include "nes_diag_runtime.h"
typedef struct {unsigned MODER,OTYPER,ODR,BSRR,AFR[2];} GPIO102;
typedef struct {unsigned CR1,CR2,SR,DR;} SPI102;
typedef struct {unsigned APB2RSTR;} RCC102;
static GPIO102 ga102,gb102;static SPI102 sp102;static RCC102 rc102;
#define GPIOA (&ga102)
#define GPIOB (&gb102)
#define SPI1 (&sp102)
#define RCC (&rc102)
#include "registers102.h"
static unsigned irq102,steps102,barriers102,observe102,terminal102;
static unsigned pending102,phase102,hwclock102,miso102,initial_rcc102;
static unsigned check_observer102,cs_seen102,forced_selected102,quiesced102;
static jmp_buf terminal_env102;
static unsigned mode102(GPIO102 *g,unsigned n){return (g->MODER>>(n*2))&3u;}
static unsigned cs102(void){return mode102(GPIOA,4)==1&&!!(ga102.ODR&16);}
static void flush_bsrr102(GPIO102 *g){g->ODR=(g->ODR&~(g->BSRR>>16))|(g->BSRR&65535);g->BSRR=0;}
static void step102(unsigned line){
 flush_bsrr102(GPIOA);flush_bsrr102(GPIOB);steps102++;
 if(cs102())cs_seen102=1;
 if(mode102(GPIOB,3)==1&&(gb102.ODR&8)==0&&!cs102())forced_selected102++;
 if(rc102.APB2RSTR&RCC_APB2RSTR_SPI1RST){sp102.CR1=sp102.CR2=0;pending102=phase102=0;quiesced102=1;}
 else if(hwclock102&&pending102){phase102=(phase102+1)%16;if(!phase102)pending102--;}
 assert(steps102<100);assert(!forced_selected102);
 printf("MMIO102 step=%u line=%u cs=%u modes=%08x odr=%08x cr1=%x cr2=%x reset=%x pending=%u phase=%u\n",steps102,line,cs102(),gb102.MODER,gb102.ODR,sp102.CR1,sp102.CR2,rc102.APB2RSTR,pending102,phase102);
}
static void assert_final102(void){
 assert(cs102()&&mode102(GPIOB,3)==1&&mode102(GPIOB,5)==1&&mode102(GPIOB,4)==0);
 assert(!(gb102.ODR&40)&&!(ga102.OTYPER&16)&&!(gb102.OTYPER&40));
 assert(!(sp102.CR1&SPI_CR1_SPE)&&sp102.CR2==0&&rc102.APB2RSTR==(initial_rcc102|RCC_APB2RSTR_SPI1RST));
 assert(!pending102&&!phase102&&quiesced102&&barriers102==3);
 assert(mode102(GPIOA,0)==1&&!(ga102.ODR&1)&&!irq102);
}
#define __DSB() (++barriers102)
#define OTG_FS_IRQn 67
#define NVIC_DisableIRQ(n) do {assert((n)==67);irq102=0;} while(0)
#define __NOP() do {assert_final102();terminal102++;longjmp(terminal_env102,1);} while(0)
uint32_t nes_diag_ticks(void){assert(!"quiesce must not query time");return 0;}
void nes_diag_observe(const struct nes_diag_report *r,bool active){
 (void)r;(void)active;if(check_observer102){assert_final102();observe102++;}
}
#include "snes102.inc"
#include "quiesce102.inc"
#include "blocked102.inc"
int main(int argc,char **argv){
 assert(argc==2);unsigned seed=(unsigned)atoi(argv[1]);setvbuf(stdout,NULL,_IONBF,0);
 /* PA0 latch LOW is established by board initialization, as snes_reset requires. */
 ga102=(GPIO102){.MODER=0xaaaaaaaa,.OTYPER=0xa55a,.ODR=0xa5a4};
 gb102=(GPIO102){.MODER=0xaaaaaaaa,.OTYPER=0x5aa5,.ODR=0x5a5a,.AFR={0x00555000,0x98765432}};
 if(seed&1)ga102.ODR|=16;else ga102.ODR&=~16u;
 ga102.MODER=(ga102.MODER&~(3u<<8))|(1u<<8);
 if(seed&2)gb102.ODR|=40;else gb102.ODR&=~40u;
 /* SPI AF5 or pre-existing GPIO transport; never change unrelated pins. */
 if(seed&4)gb102.MODER=(gb102.MODER&~((3u<<6)|(3u<<10)))|(1u<<6)|(1u<<10);
 /* Model may start on a low GPIO clock with CS low; only a forced change counts. */
 if((seed&4)&&!(seed&2))cs_seen102=0;
 sp102=(SPI102){.CR1=SPI_CR1_SPE|(seed&8?2:0),.CR2=0xe3,.SR=0x83,.DR=0x5a};
 initial_rcc102=rc102.APB2RSTR=0x4002;pending102=2;phase102=(seed>>4)&15;hwclock102=!(seed&256);miso102=1;
 irq102=1;unsigned keepa=ga102.MODER&~((3u<<8)|3u),keepb=gb102.MODER&~((3u<<6)|(3u<<8)|(3u<<10));
 unsigned oa=ga102.ODR&~16u,ob=gb102.ODR&~40u,ta=ga102.OTYPER&~16u,tb=gb102.OTYPER&~40u;
 if(!(seed&512)){nes_diag_begin();nes_diag_fail(NES_DIAG_SPI);}
 check_observer102=1;
 if(!setjmp(terminal_env102))nes_diag_blocked();
 assert(terminal102==1&&observe102==(seed&512?2u:1u));
 assert((ga102.MODER&~((3u<<8)|3u))==keepa&&(gb102.MODER&~((3u<<6)|(3u<<8)|(3u<<10)))==keepb);
 assert((ga102.ODR&~16u)==oa&&(gb102.ODR&~40u)==ob);
 assert((ga102.OTYPER&~16u)==ta&&(gb102.OTYPER&~40u)==tb&&gb102.AFR[0]==0x00555000&&gb102.AFR[1]==0x98765432);
 assert(sp102.DR==0x5a&&miso102==1&&nes_diag_status()->error==(seed&512?0:NES_DIAG_SPI));
 puts("PASS102 terminal reached without status/time wait; unrelated pins/RCC preserved");return 0;
}
