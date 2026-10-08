/* SPDX-License-Identifier: MIT */
/* Host-only MMIO/CSS effects. HSE detection, CPU/APB timing and CE are not modeled. */
RCC109 rcc109;
static jmp_buf nmi_env109;
static unsigned css_case109,nmi109,masked109,css_on109,css_off109,stores109;
static unsigned fault_cmd109,fault_edge109,fault_config109,fault_byte109,fault_frame109,fault_tx109,fault_uart109;
static void init109(void){
 if(baseline098>=200){css_case109=baseline098-200;baseline098=0;rtc_mode099=0;}
 /* Existing initialized boot state: PA1 output and RESET preload LOW.
  * Actual snes_reset changes PA0 direction before CSS begin; not forced here. */
 mock_a.MODER=(mock_a.MODER&~(3u<<2))|(1u<<2);
 mock_a.ODR=(mock_a.ODR&~1u)|2u;mock_a.IDR|=2;
 rcc109=(RCC109){.CR=RCC_CR_HSEON|RCC_CR_HSERDY|RCC_CR_PLLRDY,
  .CFGR=RCC_CFGR_SWS_PLL,.PLLCFGR=RCC_PLLCFGR_PLLSRC_HSE,.AHB1ENR=3,.CIR=0x3500,.APB2RSTR=0x4002};
 if(css_case109==20)RCC->CR&=~RCC_CR_HSERDY;
 if(css_case109==21)mock_a.MODER&=~(3u<<2);
 if(css_case109==22)RCC->CR|=RCC_CR_CSSON;
}
static void inject109(unsigned css){
 assert(!nmi109);nmi109=1;
 fault_cmd109=card_commands096();fault_edge109=card_edges096();fault_config109=configs;
 fault_byte109=config_bytes096;fault_frame109=frames;fault_tx109=tx100;fault_uart109=uart_reads103;
 if(css){RCC->CR&=~(RCC_CR_HSEON|RCC_CR_HSERDY);RCC->CFGR&=~RCC_CFGR_SWS;RCC->CIR|=RCC_CIR_CSSF;}
 NMI_Handler();assert(!"NMI returned");
}
void event109(unsigned point){
 if(nmi109||!css_on109)return;
 unsigned c=css_case109;
 if((c==1&&point==1&&configs==0)||(c==2&&point==2&&config_bytes096==64)||
    (c==3&&point==3&&config_bytes096==64)||(c==4&&point==4&&count==32)||
    (c==5&&point==5&&menu_bytes098==256)||(c==6&&point==1&&card_writes096()>0)||
    (c==7&&point==5&&release097)||(c==11&&point==6&&css_off109)||(c==12&&point==4&&count==32))inject109(c!=12);
}
uint32_t read109(uint32_t *p){return *p;}
void write109(uint32_t *p,uint32_t v){
 if(p==&RCC->CR&&!nmi109){
  if(v&RCC_CR_CSSON)css_on109++;
  else {css_off109++;if(css_case109==8)inject109(1);}
 }
 if(p==&RCC->CIR)*p=(v&0x7f00u)|((*p&RCC_CIR_CSSF)&((v&RCC_CIR_CSSC)?0u:~0u));
 else *p=v;
 if(nmi109){
  stores109++;
  if(p==&GPIOA->BSRR){
   mock_a.ODR=(mock_a.ODR&~(v>>16))|(v&65535u);mock_a.BSRR=0;
   if(v&(1u<<16))reset_held=1;
   if(v&(1u<<17)){done=0;mock_a.IDR&=~2u;}
   if(v&16)cs100=1;
  }
  if(p==&GPIOB->BSRR){mock_b.ODR=(mock_b.ODR&~(v>>16))|(v&65535u);mock_b.BSRR=0;}
  if(p==&RCC->APB2RSTR&&(v&RCC_APB2RSTR_SPI1RST)){mock_spi.CR1=mock_spi.CR2=0;pending_rx100=0;}
 }else if(p==&RCC->CR){
  if(css_case109==10&&(v&RCC_CR_CSSON))inject109(1);
  if(css_case109==9&&!(v&RCC_CR_CSSON))inject109(1);
 }
}
void mask109(void){masked109=1;}
void halt109(void){assert(nmi109);longjmp(nmi_env109,1);}
