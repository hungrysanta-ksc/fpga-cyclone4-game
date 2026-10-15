/* SPDX-License-Identifier: MIT */
/* RUN-only SPI1 full-duplex DMA. RM0368 sections9.3.17,20.3.8,20.3.9.
 * Same2.625MHz/SS boundaries/CRC. CPU keeps checking ownership while DMA
 * moves bytes; no DMA IRQ, retry, queued packet or additional data buffer.
 * Never return a caller's stack buffer while a DMA stream can still use it.
 */
#ifndef NES182_READ
#define NES182_READ(reg) (reg)
#define NES182_WRITE(reg,value) ((reg)=(value))
#define NES182_ADDRESS(p) ((uint32_t)(uintptr_t)(p))
#endif
#define NES182_DONE (DMA_LISR_TCIF0|DMA_LISR_TCIF3)
#define NES182_ERRORS (DMA_LISR_TEIF0|DMA_LISR_DMEIF0|DMA_LISR_FEIF0|DMA_LISR_TEIF3|DMA_LISR_DMEIF3|DMA_LISR_FEIF3)
#define NES182_CLEAR (NES182_DONE|NES182_ERRORS|DMA_LISR_HTIF0|DMA_LISR_HTIF3)
struct nes182_stream {uint32_t cr,ndtr,par,m0ar,m1ar,fcr;};
struct nes182_saved {struct nes182_stream rx,tx;};
static bool nes182_available(void){
 return (NES182_READ(RCC->AHB1ENR)&RCC_AHB1ENR_DMA2EN) &&
  !((NES182_READ(DMA2_Stream0->CR)|NES182_READ(DMA2_Stream3->CR))&DMA_SxCR_EN) &&
  !NVIC_GetEnableIRQ(DMA2_Stream0_IRQn) && !NVIC_GetEnableIRQ(DMA2_Stream3_IRQn) &&
  !NVIC_GetPendingIRQ(DMA2_Stream0_IRQn) && !NVIC_GetPendingIRQ(DMA2_Stream3_IRQn);
}
static void nes182_save(DMA_Stream_TypeDef *s,struct nes182_stream *v){
 v->cr=NES182_READ(s->CR);v->ndtr=NES182_READ(s->NDTR);
 v->par=NES182_READ(s->PAR);v->m0ar=NES182_READ(s->M0AR);
 v->m1ar=NES182_READ(s->M1AR);v->fcr=NES182_READ(s->FCR);
}
static void nes182_restore_stream(DMA_Stream_TypeDef *s,const struct nes182_stream *v){
 NES182_WRITE(s->NDTR,v->ndtr);NES182_WRITE(s->PAR,v->par);
 NES182_WRITE(s->M0AR,v->m0ar);NES182_WRITE(s->M1AR,v->m1ar);
 NES182_WRITE(s->FCR,v->fcr);NES182_WRITE(s->CR,v->cr);
}
static void nes182_claim(struct nes182_saved *save,const uint8_t *tx,uint8_t *rx,unsigned n){
 nes182_save(DMA2_Stream0,&save->rx);nes182_save(DMA2_Stream3,&save->tx);
 NES182_WRITE(DMA2->LIFCR,NES182_CLEAR);
 NES182_WRITE(DMA2_Stream0->PAR,NES182_ADDRESS(&SPI1->DR));
 NES182_WRITE(DMA2_Stream3->PAR,NES182_ADDRESS(&SPI1->DR));
 NES182_WRITE(DMA2_Stream0->M0AR,NES182_ADDRESS(rx));
 NES182_WRITE(DMA2_Stream3->M0AR,NES182_ADDRESS(tx));
 NES182_WRITE(DMA2_Stream0->NDTR,n);NES182_WRITE(DMA2_Stream3->NDTR,n);
 NES182_WRITE(DMA2_Stream0->FCR,0);NES182_WRITE(DMA2_Stream3->FCR,0);
 NES182_WRITE(DMA2_Stream0->CR,(3u<<DMA_SxCR_CHSEL_Pos)|(3u<<DMA_SxCR_PL_Pos)|DMA_SxCR_MINC);
 NES182_WRITE(DMA2_Stream3->CR,(3u<<DMA_SxCR_CHSEL_Pos)|(2u<<DMA_SxCR_PL_Pos)|DMA_SxCR_MINC|DMA_SxCR_DIR_0);
}
static bool nes182_run(void){
 /* The CS-settling callback can latch a timer/session fault. Check before
  * enabling any DMA request, not only after autonomous transfer has begun. */
 if(!nes_cf86_check094())return false;
 __DMB();
 NES182_WRITE(DMA2_Stream0->CR,NES182_READ(DMA2_Stream0->CR)|DMA_SxCR_EN);
 NES182_WRITE(SPI1->CR2,SPI_CR2_RXDMAEN);
 NES182_WRITE(DMA2_Stream3->CR,NES182_READ(DMA2_Stream3->CR)|DMA_SxCR_EN);
 NES182_WRITE(SPI1->CR2,SPI_CR2_RXDMAEN|SPI_CR2_TXDMAEN);
 unsigned last=0xffffffffu,idle=0;
 for(unsigned i=0;i<131072u;i++){
  if(!nes_cf86_check094())return false;
  uint32_t flags=NES182_READ(DMA2->LISR);
  if((flags&NES182_ERRORS)||(NES165_SR()&NES165_ERRORS))return false;
  unsigned left=NES182_READ(DMA2_Stream0->NDTR)+NES182_READ(DMA2_Stream3->NDTR);
  if((flags&NES182_DONE)==NES182_DONE && !left){__DMB();return true;}
  if(left==last){if(++idle==1024u)return false;}else {last=left;idle=0;}
 }
 return false;
}
static void nes182_stuck(void) __attribute__((noreturn,noinline));
static void nes182_stuck(void){
 /* Requests are off. Keep the caller's buffers alive if EN never clears.
  * Existing CSS NMI also disables SPI requests/SPI and never returns. */
 __disable_irq();GPIOA->BSRR=1u<<4;SPI1->CR1&=~SPI_CR1_SPE;
 (void)nes_cf86_fail094();
 for(;;)__NOP();
}
static void nes182_restore(const struct nes182_saved *save){
 NES182_WRITE(SPI1->CR2,0);
 NES182_WRITE(DMA2_Stream0->CR,NES182_READ(DMA2_Stream0->CR)&~DMA_SxCR_EN);
 NES182_WRITE(DMA2_Stream3->CR,NES182_READ(DMA2_Stream3->CR)&~DMA_SxCR_EN);
 for(unsigned i=0;;i++){
  if(!((NES182_READ(DMA2_Stream0->CR)|NES182_READ(DMA2_Stream3->CR))&DMA_SxCR_EN))break;
  if(i==1023u)nes182_stuck();
 }
 __DMB();NES182_WRITE(DMA2->LIFCR,NES182_CLEAR);
 nes182_restore_stream(DMA2_Stream0,&save->rx);
 nes182_restore_stream(DMA2_Stream3,&save->tx);
}
