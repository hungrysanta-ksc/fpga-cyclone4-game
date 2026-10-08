/* SPDX-License-Identifier: MIT */
static unsigned pin_bit091,pin_byte091,pin_edges091,pin_low091;
static uint32_t pin_saved_modes091;
uint8_t SPI_OFFLOAD;
void pin_init091(void);void pin_post091(void);void pin_spi091(void);
void pin_prog091(uint8_t);void pin_cclk091(uint8_t);
int pin_done091(void);int pin_status091(void);
static unsigned mode091(struct gpio088 *g,unsigned n){return (g->MODER>>(n*2))&3;}
static void bus_ready091(void){
 assert(mode091(GPIOB,3)==2&&mode091(GPIOB,4)==2&&mode091(GPIOB,5)==2);
 assert((GPIOB->AFR[0]&0x00fff000)==0x00555000);
 assert((GPIOB->OSPEEDR&0xfc0)==0xa80&&((GPIOA->OSPEEDR>>8)&3)==2);
 assert(SPI1->CR1==0x344&&!(SPI1->SR&SPI_SR_BSY));
 assert(mode091(GPIOB,8)==0&&mode091(GPIOB,9)==1&&mode091(GPIOA,4)==1);
 assert(!pin_bit091&&!((GPIOB->ODR>>9)&1));
}
void pin_out091(struct gpio088 *r,unsigned p,unsigned v){
 v=!!v;unsigned old=(r->ODR>>p)&1;
 if(v)r->ODR|=1u<<p;else r->ODR&=~(1u<<p);
 if(r==GPIOA&&p==1){assert(mode091(r,p)==1);if(nes_return_failed())assert(!v);prog=v;return;}
 if(r==GPIOB&&p==8){assert(held&&!nes_return_failed()&&mode091(r,p)==1);return;}
 assert(r==GPIOB&&p==9&&mode091(r,p)==1);
 if(nes_return_failed()){assert(!v);return;}
 if(!old&&v){
  assert(held&&prog&&mode091(GPIOB,8)==1);
  assert((GPIOB->MODER&0xfc0)==pin_saved_modes091);
  unsigned limit=clock_cycle==2?510856:153544;
  if(sent==limit){assert(clock_cycle==2&&!pin_bit091);clock_extra++;}
  else{
   const uint8_t *expected=clock_cycle==2?clock_raw:golden_mini;
   unsigned bit=(GPIOB->ODR>>8)&1;assert(bit==((expected[sent]>>pin_bit091)&1));
   pin_byte091|=bit<<pin_bit091;
   if(++pin_bit091==8){send_byte((uint8_t)pin_byte091);pin_bit091=pin_byte091=0;}
  }
  pin_edges091++;
 }else if(old&&!v)pin_low091++;
}
unsigned pin_read091(uint32_t *r,unsigned p){
 if(r==&GPIOB->IDR&&p==4){assert(mode091(GPIOB,4)==0&&mode091(GPIOB,3)==1&&mode091(GPIOB,5)==1&&!(SPI1->CR1&SPI_CR1_SPE));return model_input();}
 if(r==&GPIOA->IDR&&p==1)return read_prog();
 if(r==&GPIOA->IDR&&p==15){assert(mode091(GPIOA,15)==0);return clock_cycle==2?!clock_done_fail&&sent==510856&&clock_extra>=3:pinfault==3?1:pinfault==4?0:sent==153544;}
 assert(r==&GPIOB->IDR&&p==7&&mode091(GPIOB,7)==0);
 if(clock_cycle==2&&clock_status_fail&&sent>=clock_status_fail)return 0;
 return pinfault==2?0:prog;
}
