/* SPDX-License-Identifier: MIT */
/* Actual driver, asynchronous register model. Not STM32 timing simulation. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <setjmp.h>
#include "nes_rom_spi.h"
#define SPI_SR_RXNE 1u
#define SPI_SR_TXE 2u
#define SPI_SR_CRCERR 16u
#define SPI_SR_MODF 32u
#define SPI_SR_OVR 64u
#define SPI_SR_BSY 128u
#define SPI_SR_FRE 256u
#define SPI_CR1_MSTR 4u
#define SPI_CR1_BR_Pos 3u
#define SPI_CR1_SPE 64u
#define SPI_CR1_SSI 256u
#define SPI_CR1_SSM 512u
#define SPI_CR2_RXDMAEN 1u
#define SPI_CR2_TXDMAEN 2u
#define RCC_CFGR_HPRE 0xf0u
#define RCC_CFGR_PPRE2 0xe000u
#define RCC_AHB1ENR_DMA2EN (1u<<22)
#define DMA_SxCR_EN 1u
#define DMA_SxCR_DIR_0 (1u<<6)
#define DMA_SxCR_MINC (1u<<10)
#define DMA_SxCR_PL_Pos 16u
#define DMA_SxCR_CHSEL_Pos 25u
#define DMA_LISR_FEIF0 1u
#define DMA_LISR_DMEIF0 4u
#define DMA_LISR_TEIF0 8u
#define DMA_LISR_HTIF0 16u
#define DMA_LISR_TCIF0 32u
#define DMA_LISR_FEIF3 (1u<<22)
#define DMA_LISR_DMEIF3 (4u<<22)
#define DMA_LISR_TEIF3 (8u<<22)
#define DMA_LISR_HTIF3 (16u<<22)
#define DMA_LISR_TCIF3 (32u<<22)
#define DMA2_Stream0_IRQn 0
#define DMA2_Stream3_IRQn 1
typedef struct {uint32_t CR,NDTR,PAR,M0AR,M1AR,FCR;} DMA_Stream_TypeDef;
static DMA_Stream_TypeDef streams[2],saved_streams[2];
static struct {uint32_t CR1,CR2,SR,DR;} spi;
static struct {uint32_t MODER,AFR[2],BSRR;} gpio,gpioa;
static struct {uint32_t CFGR,AHB1ENR;} rcc;
static struct {uint32_t LISR,LIFCR;} dma;
#define SPI1 (&spi)
#define GPIOB (&gpio)
#define GPIOA (&gpioa)
#define RCC (&rcc)
#define DMA2 (&dma)
#define DMA2_Stream0 (&streams[0])
#define DMA2_Stream3 (&streams[1])
static uint8_t tx_data[261],rx_data[261],sent[259];
static unsigned count,tx_at,rx_at,period,cycles,guard_checks,fail_check,wait_calls;
static unsigned fault_byte,dma_fault,spi_fault,stall,stuck_disable,disable_delay[2],fail_wait;
static unsigned irq_enabled,irq_pending,pending_rx,early_tx_done;
static bool gpio_owned,failed,selected,monitoring,halted;
static jmp_buf escape;
static void step(void){
 cycles++;
 for(unsigned i=0;i<2;i++)if(disable_delay[i]&&!--disable_delay[i])streams[i].CR&=~1u;
 if(stall==1 || !selected || !(spi.CR1&SPI_CR1_SPE) || !(spi.CR2&2u) || cycles%period)return;
 if(fault_byte&&tx_at>=fault_byte){dma.LISR|=dma_fault;spi.SR|=spi_fault;return;}
 if(pending_rx){
  if(stall==2)return;
  assert((spi.CR2&1u)&&(streams[0].CR&1u)&&streams[0].NDTR);
  rx_data[1+rx_at]=sent[rx_at]^0x96u;rx_at++;streams[0].NDTR--;pending_rx=0;
  if(!streams[0].NDTR){streams[0].CR&=~1u;dma.LISR|=DMA_LISR_TCIF0;}
  if(stall!=3)spi.SR&=~SPI_SR_BSY;
 }
 if((streams[1].CR&1u)&&streams[1].NDTR){
  assert(!failed && tx_at<count && (streams[0].CR&1u));
  assert(streams[0].PAR==0x1000&&streams[1].PAR==0x1000);
  assert(streams[0].M0AR==0x3000&&streams[1].M0AR==0x2000);
  assert(streams[0].CR==((3u<<25)|(3u<<16)|DMA_SxCR_MINC|1));
  assert(streams[1].CR==((3u<<25)|(2u<<16)|DMA_SxCR_MINC|DMA_SxCR_DIR_0|1));
  sent[tx_at]=tx_data[1+tx_at];tx_at++;streams[1].NDTR--;
  pending_rx=1;spi.SR=SPI_SR_TXE|SPI_SR_BSY;
  if(!streams[1].NDTR){streams[1].CR&=~1u;dma.LISR|=DMA_LISR_TCIF3;early_tx_done++;}
 }
}
static uint32_t rd(uint32_t *r){step();return *r;}
static void wr(uint32_t *r,uint32_t v){
 if(r==&dma.LIFCR){dma.LISR&=~v;dma.LIFCR=v;return;}
 for(unsigned i=0;i<2;i++)if(r==&streams[i].CR && (*r&1u) && !(v&1u)){
  if(stuck_disable)return;
  disable_delay[i]=3;*r=v|1u;return;
 }
 *r=v;
}
static uint32_t address(const void *p){
 if(p==&spi.DR)return 0x1000;
 if(p==tx_data+1)return 0x2000;
 assert(p==rx_data+1);return 0x3000;
}
static unsigned NVIC_GetEnableIRQ(unsigned n){return (irq_enabled>>n)&1u;}
static unsigned NVIC_GetPendingIRQ(unsigned n){return (irq_pending>>n)&1u;}
static bool nes_cf86_monitoring094(void){return monitoring;}
static bool nes_cf86_fail094(void){failed=true;return false;}
static bool nes_cf86_check094(void){
 guard_checks++;if(fail_check==guard_checks)failed=true;return !failed;
}
static uint8_t read_dr(void){uint8_t v=spi.DR;spi.SR&=~(SPI_SR_RXNE|SPI_SR_OVR);return v;}
static void halt(void){halted=true;longjmp(escape,1);}
#define __DMB() ((void)0)
#define __disable_irq() ((void)0)
#define __NOP() halt()
#define NES165_SR() rd(&spi.SR)
#define NES165_READ() read_dr()
#define NES165_WRITE(v) assert(!"CPU must not move DMA bytes")
#define NES182_READ(reg) rd(&(reg))
#define NES182_WRITE(reg,value) wr(&(reg),(value))
#define NES182_ADDRESS(p) address(p)
#include "nes_native165_bulk.inc"
static void select_io(void *ctx,bool v){
 (void)ctx;
 if(!v && selected && !failed && !stall && !dma_fault && !spi_fault){assert(rx_at==count&&!pending_rx);}
 selected=v;
}
static void wait_io(void *ctx,unsigned us){(void)ctx;assert(us==2);wait_calls++;if(wait_calls==fail_wait)failed=true;}
static const struct nes_rom_spi_io io={0,select_io,0,0,0,wait_io};
static void reset(unsigned n,unsigned speed){
 memset(&spi,0,sizeof spi);spi.CR1=0x304;spi.SR=SPI_SR_TXE;
 memset(&dma,0,sizeof dma);dma.LISR=(1u<<6)|(1u<<16); /* Other streams' flags. */
 for(unsigned i=0;i<2;i++)streams[i]=(DMA_Stream_TypeDef){0x300,7+i,11+i,21+i,31+i,3};
 memcpy(saved_streams,streams,sizeof streams);
 gpio.MODER=0xa5000000|NES165_GPIO_MODE;gpio.AFR[0]=0x00555000;gpioa.BSRR=0;
 rcc.CFGR=0;rcc.AHB1ENR=RCC_AHB1ENR_DMA2EN;
 count=n;period=speed;tx_at=rx_at=cycles=guard_checks=fail_check=wait_calls=0;
 fault_byte=dma_fault=spi_fault=stall=stuck_disable=irq_enabled=irq_pending=pending_rx=early_tx_done=fail_wait=0;
 disable_delay[0]=disable_delay[1]=0;
 gpio_owned=monitoring=true;failed=selected=halted=false;
 memset(rx_data,0xa5,sizeof rx_data);for(unsigned i=0;i<sizeof tx_data;i++)tx_data[i]=(uint8_t)(i*73u);
}
static void stopped(void){
 assert(!selected&&!(spi.CR1&SPI_CR1_SPE)&&!spi.CR2&&spi.CR1==0x304);
 assert(gpio.MODER==(0xa5000000|NES165_GPIO_MODE));
 assert(!memcmp(streams,saved_streams,sizeof streams));
 assert(dma.LISR==((1u<<6)|(1u<<16)));
 assert(rx_data[0]==0xa5 && rx_data[count+1]==0xa5);
}
static bool run(void){return nes_native165_bulk(&io,tx_data+1,rx_data+1,count);}
int main(void){
 unsigned cases=0,guards=0,errors=0;
 for(unsigned n=1;n<=259;n++)for(unsigned d=1;d<=17;d+=8){
  reset(n,d);assert(run());stopped();assert(tx_at==n&&rx_at==n&&early_tx_done==1&&wait_calls==4);
  assert(!memcmp(tx_data+1,sent,n));for(unsigned i=0;i<n;i++)assert(rx_data[i+1]==(uint8_t)(tx_data[i+1]^0x96));cases++;
 }
 for(unsigned n=1;n<=259;n+=129){
  reset(n,9);assert(run());unsigned checks=guard_checks;
  for(unsigned i=1;i<=checks;i++){
   reset(n,9);fail_check=i;assert(!run()&&failed);stopped();
   unsigned before=tx_at;assert(!run()&&tx_at==before);guards++;
  }
 }
 const unsigned ds[]={DMA_LISR_FEIF0,DMA_LISR_DMEIF0,DMA_LISR_TEIF0,DMA_LISR_FEIF3,DMA_LISR_DMEIF3,DMA_LISR_TEIF3};
 const unsigned ss[]={SPI_SR_OVR,SPI_SR_MODF,SPI_SR_CRCERR,SPI_SR_FRE};
 for(unsigned n=1;n<=259;n++)for(unsigned k=0;k<10;k++){
  reset(259,9);fault_byte=n;if(k<6)dma_fault=ds[k];else spi_fault=ss[k-6];
  assert(!run()&&failed&&tx_at==n);stopped();errors++;
 }
 for(unsigned i=1;i<=3;i++){reset(259,9);stall=i;assert(!run()&&failed);stopped();cases++;}
 /* A stream that refuses disable must retain stack ownership, never return. */
 reset(259,9);stall=1;stuck_disable=1;
 if(!setjmp(escape)){(void)run();assert(!"unquiesced DMA returned");}
 assert(halted&&failed&&!spi.CR2&&!(spi.CR1&SPI_CR1_SPE)&&gpioa.BSRR==(1u<<4));cases++;
 for(unsigned i=0;i<6;i++){
  reset(16,9);
  if(i<2)streams[i].CR|=1u;else if(i<4)irq_enabled=1u<<(i-2);else irq_pending=1u<<(i-4);
  DMA_Stream_TypeDef before[2];memcpy(before,streams,sizeof before);
  assert(!run()&&failed&&!tx_at&&!memcmp(before,streams,sizeof before));cases++;
 }
 reset(16,9);rcc.AHB1ENR=0;assert(!run()&&failed&&!tx_at);cases++;
 reset(0,9);assert(!run()&&!tx_at);reset(260,9);assert(!run()&&!tx_at);cases+=2;
 for(unsigned i=1;i<=4;i++){reset(259,9);fail_wait=i;assert(!run()&&failed);stopped();if(i<3)assert(!tx_at);cases++;}
 printf("PASS DMA182 normal_and_boundary=%u guard_faults=%u byte_errors=%u maxbytes=259\n",cases,guards,errors);
 return 0;
}
