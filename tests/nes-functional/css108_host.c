/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <setjmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "config.h"
#include "nes_diag_runtime.h"
#include "nes_menu_return.h"
static jmp_buf jump;
GPIO_TypeDef ga,gb;RCC_TypeDef rc;SPI_TypeDef sp;
static unsigned usb,masked,ops,writes,observed,nops,inject,inject_after,disabled;
static bool sd_fault;
static char trace[8192];static size_t trace_n;
static void injection(void){
 if(inject&&ops==inject){
  inject=0;rc.CR&=~RCC_CR_HSERDY;
  if(rc.CR&RCC_CR_CSSON){rc.CIR|=RCC_CIR_CSSF;NMI_Handler();}
 }
}
uint32_t read108(volatile uint32_t *p){ops++;if(!inject_after)injection();uint32_t v=*p;if(inject_after)injection();return v;}
void write108(volatile uint32_t *p,uint32_t v,const char *name){
 ops++;if(!inject_after)injection();writes++;
 trace_n+=(size_t)snprintf(trace+trace_n,sizeof(trace)-trace_n,"%s=%08x\n",name,v);
 if(p==&ga.BSRR){ga.ODR|=v&0xffff;ga.ODR&=~(v>>16);}
 else if(p==&gb.BSRR){gb.ODR|=v&0xffff;gb.ODR&=~(v>>16);}
 if(p==&rc.CIR){rc.CIR=(rc.CIR&0xffu)|(v&0x7f00u);if(v&RCC_CIR_CSSC)rc.CIR&=~RCC_CIR_CSSF;}
 else *p=v;
 if(inject_after)injection();
}
void mask108(void){masked=1;}
unsigned getusb108(void){return usb;}
void disableusb108(void){usb=0;disabled++;}
void halt108(void){nops++;longjmp(jump,1);}
uint32_t nes_diag_ticks(void){return 123;}
void nes_diag_observe(const struct nes_diag_report *r,bool a){(void)r;(void)a;observed++;}
bool nes_diag_sd_failed(void){return sd_fault;}
void nes_diag_blocked(void){longjmp(jump,2);}
#include "nes_css108.c"
#include "nes_diag_runtime.c"
/* Actual production return predicates/reset; other file operations excluded. */
#include "return108.inc"
static void setup(void){
 memset(&ga,0,sizeof ga);memset(&gb,0,sizeof gb);memset(&rc,0,sizeof rc);memset(&sp,0,sizeof sp);
 owned108=claimed108=fault108=0;fault=log_allowed=io_active=false;active=false;sd_fault=false;
 usb=masked=ops=writes=observed=nops=inject=inject_after=disabled=0;trace_n=0;trace[0]=0;
 ga.MODER=0xa0000005;ga.ODR=0x8002;ga.OTYPER=0x100;gb.MODER=0xaaaaaaaa;gb.ODR=0xffff;
 rc.AHB1ENR=3;rc.CR=RCC_CR_HSEON|RCC_CR_HSERDY|RCC_CR_PLLRDY;
 rc.PLLCFGR=RCC_PLLCFGR_PLLSRC_HSE;rc.CFGR=RCC_CFGR_SWS_PLL;rc.CIR=0x3500;
 sp.CR1=SPI_CR1_SPE|0x21;sp.CR2=0x33;nes_diag_begin();
}
static void isolated(unsigned reason){
 assert(nes_css_fault108()==reason&&masked&&disabled&&nops==1);
 assert(!(ga.ODR&3u)&&(ga.ODR&(1u<<4))&&(ga.MODER&3u)==1);
 assert(!(gb.ODR&((1u<<3)|(1u<<5))));
 assert((gb.MODER&((3u<<6)|(3u<<8)|(3u<<10)))==((1u<<6)|(1u<<10)));
 assert(!(sp.CR1&SPI_CR1_SPE)&&!sp.CR2&&(rc.APB2RSTR&RCC_APB2RSTR_SPI1RST));
 assert(!(rc.CIR&RCC_CIR_CSSF)&&(rc.CIR&0x7f00)==0x3500);
 const char *nc=strstr(trace,"GPIOA->BSRR=00020000"),*cs=strstr(trace,"GPIOA->BSRR=00000010");
 assert(nc&&cs&&nc<cs);assert(observed==1); /* no callback from NMI */
 nes_return_reset();assert(nes_return_failed()); /* sticky CSS survives legacy reset */
 assert(!nes_css_begin108()&&!nes_css_end108());
 unsigned prior=observed;int j=setjmp(jump);if(!j)nes_diag_leave();assert(j==2&&active&&observed==prior);
}
int main(int argc,char **argv){
 assert(argc==2);unsigned c=(unsigned)strtoul(argv[1],0,10);setup();
 if(c<18){
  switch(c){
   case 0:active=false;break;case 1:fault=true;break;case 2:usb=1;break;
   case 3:rc.AHB1ENR=1;break;case 4:rc.AHB1ENR=2;break;case 5:ga.MODER&=~3u;break;
   case 6:ga.MODER&=~12u;break;case 7:ga.ODR|=1;break;case 8:rc.CR|=RCC_CR_CSSON;break;
   case 9:rc.CIR|=RCC_CIR_CSSF;break;case 10:rc.CR&=~RCC_CR_HSEON;break;
   case 11:rc.CR&=~RCC_CR_HSERDY;break;case 12:rc.CR&=~RCC_CR_PLLRDY;break;
   case 13:rc.PLLCFGR=0;break;case 14:rc.CFGR=0;break;case 15:owned108=1;break;
   case 16:fault108=1;break;case 17:sd_fault=true;break;
  }
  uint32_t original=rc.CR;assert(!nes_css_begin108());assert(!writes&&rc.CR==original);
 }else if(c==18||c==19){
  masked=c-18;assert(nes_css_begin108());assert(ops==11);assert(rc.CR&RCC_CR_CSSON);assert(masked==c-18);
  assert(!nes_css_begin108());ops=0;nes_diag_leave();assert(ops==6);assert(!owned108&&claimed108&&!active);
  assert(!(rc.CR&RCC_CR_CSSON)&&!fault108&&masked==c-18&&observed==2);
 }else if(c==20){
  assert(nes_css_begin108());fault=true;assert(!nes_css_end108()&&owned108&&(rc.CR&RCC_CR_CSSON));
 }else if(c==21||c==22){
  if(c==22)rc.CIR|=RCC_CIR_CSSF;
  int j=setjmp(jump);if(!j)NMI_Handler();assert(j==1&&!fault108&&!writes&&!masked&&!disabled);
 }else if(c>=23&&c<=26){
  assert(nes_css_begin108());if(c>=25)assert(nes_css_end108());
  if(c!=24&&c!=26){rc.CIR|=RCC_CIR_CSSF;rc.CR&=~RCC_CR_HSERDY;}
  unsigned before=writes;int j=setjmp(jump);if(!j)NMI_Handler();assert(j==1);
  if(c==26)assert(!fault108&&writes==before&&!masked);else isolated(c==24?2:1);
 }else if(c==27){
  assert(nes_css_begin108());rc.CR&=~RCC_CR_HSERDY;
  int j=setjmp(jump);if(!j)(void)nes_css_end108();assert(j==1);isolated(1);
 }else if(c==28){
  nes_diag_leave();assert(!writes&&!fault108&&!active&&observed==2);
 }else if(c>=100){
  /* Every MMIO boundary of begin (100s) or end (200s), before/after.
   * Synthetic register/event injection is not measured HSE failure latency. */
  unsigned end=c>=200,code=c-(end?200:100);if(end)assert(nes_css_begin108());
  ops=0;inject=code/2+1;inject_after=code%2;
  int j=setjmp(jump);
  if(!j){bool ok=end?nes_css_end108():nes_css_begin108();assert(!ok||!inject||!(rc.CR&RCC_CR_HSERDY));}
  if(j){assert(j==1);isolated(1);}else assert(!fault108);
 }else assert(0);
 printf("PASS108 case=%u fault=%u writes=%u owned=%u\n%s",c,(unsigned)fault108,writes,(unsigned)owned108,trace);
 return 0;
}
