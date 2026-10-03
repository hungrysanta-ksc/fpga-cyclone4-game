/* Sd2iec - SD/MMC to Commodore serial bus interface/controller
   Copyright (C) 2007-2010  Ingo Korb <ingo@akana.de>

   Inspiration and low-level SD/MMC access based on code from MMC2IEC
     by Lars Pontoppidan et al., see sdcard.c|h and config.h.

   FAT filesystem access based on code from ChaN and Jim Brain, see ff.c|h.

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; version 2 of the License only.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


   spi.c: Low-level SPI routines

*/

#include "config.h"
#include "bits.h"
#include "spi.h"
#include "uart.h"
#include "fpga.h"
#include "timer.h"
#include "fpga_spi.h"

/* C18: >=500ns post-byte gap (42 cycles at 84MHz). The shipping
 * SPI/command/SRAM/PSRAM RTL is phase-tested at 42MHz SPI; retain
 * FPGA_WAIT_RDY after the CDC admission window. Enabled only for
 * reset-held renderer/game verified loading.
 * CYCCNT is never reset. Restore only enable bits we acquired. */
static uint8_t gbc_load_dwt_active,gbc_load_dwt_used;
static uint8_t gbc_load_owned_trace,gbc_load_owned_counter;
static uint32_t gbc_load_dwt_fallbacks;
#define GBC_LOAD_GAP_CYCLES ((CONFIG_CPU_FREQUENCY+1999999u)/2000000u)
void spi_gbc_load_end(void) {
  gbc_load_dwt_active=0;
  if(gbc_load_owned_counter)DWT->CTRL&=~DWT_CTRL_CYCCNTENA_Msk;
  if(gbc_load_owned_trace)CoreDebug->DEMCR&=~CoreDebug_DEMCR_TRCENA_Msk;
  gbc_load_owned_counter=gbc_load_owned_trace=0;
}
void spi_gbc_load_begin(void) {
  spi_gbc_load_end();gbc_load_dwt_used=0;gbc_load_dwt_fallbacks=0;
  if(DWT->CTRL&DWT_CTRL_NOCYCCNT_Msk)return;
  gbc_load_owned_trace=!(CoreDebug->DEMCR&CoreDebug_DEMCR_TRCENA_Msk);
  gbc_load_owned_counter=!(DWT->CTRL&DWT_CTRL_CYCCNTENA_Msk);
  CoreDebug->DEMCR|=CoreDebug_DEMCR_TRCENA_Msk;
  DWT->CTRL|=DWT_CTRL_CYCCNTENA_Msk;
  uint32_t start=DWT->CYCCNT;
  for(unsigned i=0;i<32;i++)__NOP();
  if((uint32_t)(DWT->CYCCNT-start)>0)gbc_load_dwt_active=gbc_load_dwt_used=1;
}
unsigned spi_gbc_load_dwt_used(void) {return gbc_load_dwt_used;}
unsigned spi_gbc_load_fallbacks(void) {return gbc_load_dwt_fallbacks;}
static void gbc_spi_byte_gap(void) {
  if(gbc_load_dwt_active) {
    uint32_t start=DWT->CYCCNT;
    for(unsigned i=0;i<128;i++) {
      if((uint32_t)(DWT->CYCCNT-start)>=GBC_LOAD_GAP_CYCLES)return;
    }
    /* Counter stopped/unavailable: keep the original timed gap and stop
     * using CYCCNT for the rest of this load. Never spin indefinitely. */
    gbc_load_dwt_active=0;gbc_load_dwt_fallbacks++;
  }
  delay_us(1);
}
/* C18 gap helper end */

void spi_preinit() {

}

void spi_init() {

  /* configure & enable SPI1 -
     master mode
     clk = pclk/2 = 42MHz
     bits = 8
     CPHA = 0
     CPOL = 0
     SS software controlled
   */
  SPI1->CR1 = SPI_CR1_SSM | SPI_CR1_SSI | SPI_CR1_SPE | SPI_CR1_MSTR
            | (0b000 << SPI_CR1_BR_Pos);
  /* connect SPI1 (FPGA) on PB3,PB4,PB5 (SS -PA4- remains as GPIO) */
  GPIOB->AFR[0] |= (5 << GPIO_AFRL_AFSEL3_Pos) | (5 << GPIO_AFRL_AFSEL4_Pos)
                 | (5 << GPIO_AFRL_AFSEL5_Pos);
  GPIO_MODE_AF(GPIOB, 3);
  GPIO_MODE_AF(GPIOB, 4);
  GPIO_MODE_AF(GPIOB, 5);
  GPIO_SPEED(GPIOB, 3, IO_SPEED_H);
  GPIO_SPEED(GPIOB, 4, IO_SPEED_H);
  GPIO_SPEED(GPIOB, 5, IO_SPEED_H);
  GPIO_SPEED(FPGA_SSREG, FPGA_SSBIT, IO_SPEED_H);
  GPIO_PULLNONE(GPIOB, 4);
  GPIO_MODE_OUT(FPGA_SSREG, FPGA_SSBIT);
}

void spi_tx_sync() {
  /* Wait until TX fifo is flushed */
  while (BITBAND(SPI1->SR, SPI_SR_BSY_Pos));
}

void spi_tx_byte(uint8_t data) {
  /* Wait until TX fifo can accept data */
  while (!BITBAND(SPI1->SR, SPI_SR_TXE_Pos)) ;

  /* Send byte */
  SPI1->DR = data;
  /* The GBC command engine runs at 33.55 MHz. Leave its byte CDC and memory
   * completion time before the next byte (stock cores retain their speed). */
  if(gbc_spi_pacing) { spi_tx_sync(); gbc_spi_byte_gap(); }
}

uint8_t spi_txrx_byte(uint8_t data) {
  /* Wait until SSP is not busy */
  while (BITBAND(SPI1->SR, SPI_SR_BSY_Pos)) ;

  /* Clear RX fifo */
  while (BITBAND(SPI1->SR, SPI_SR_RXNE_Pos))
    (void) SPI1->DR;

  /* Transmit a single byte */
  SPI1->DR = data;

  /* Wait until answer has been received */
  while (!BITBAND(SPI1->SR, SPI_SR_RXNE_Pos)) ;

  uint8_t result = SPI1->DR;
  if(gbc_spi_pacing) gbc_spi_byte_gap();
  return result;
}

uint8_t spi_rx_byte() {
  /* Wait until SSP is not busy */
  while (BITBAND(SPI1->SR, SPI_SR_BSY_Pos)) ;

  /* Clear RX fifo */
  while (BITBAND(SPI1->SR, SPI_SR_RXNE_Pos))
    (void) SPI1->DR;

  /* Transmit a single dummy byte */
  SPI1->DR = 0xff;

  /* Wait until answer has been received */
  while (!BITBAND(SPI1->SR, SPI_SR_RXNE_Pos)) ;

  uint8_t result = SPI1->DR;
  if(gbc_spi_pacing) gbc_spi_byte_gap();
  return result;
}

void spi_tx_block(const void *ptr, unsigned int length) {
  const uint8_t *data = (const uint8_t *)ptr;

  while (length--) {
  /* Wait until TX fifo can accept data */
    while (!BITBAND(SPI1->SR, SPI_SR_TXE_Pos)) ;

    SPI1->DR = *data++;
  }
}

void spi_rx_block(void *ptr, unsigned int length) {
  uint8_t *data = (uint8_t *)ptr;
  unsigned int txlen = length;

  /* Wait until SSP is not busy */
  while (BITBAND(SPI1->SR, SPI_SR_BSY_Pos)) ;

  /* Clear RX fifo */
  while (BITBAND(SPI1->SR, SPI_SR_RXNE_Pos))
    (void) SPI1->DR;

  if ((length & 3) != 0 || ((uint32_t)ptr & 3) != 0) {
    /* Odd length or unaligned buffer */
    while (length > 0) {
      /* Wait until TX or RX FIFO are ready */
      while (txlen > 0 && !BITBAND(SPI1->SR, SPI_SR_TXE_Pos) &&
             !BITBAND(SPI1->SR, SPI_SR_RXNE_Pos)) ;

      /* Try to receive data */
      while (length > 0 && BITBAND(SPI1->SR, SPI_SR_RXNE_Pos)) {
        *data++ = SPI1->DR;
        length--;
      }

      /* Send dummy data until TX full or RX ready */
      while (txlen > 0 && BITBAND(SPI1->SR, SPI_SR_TXE_Pos) && !BITBAND(SPI1->SR, SPI_SR_RXNE_Pos)) {
        txlen--;
        SPI1->DR = 0xff;
      }
    }
  } else {
    /* Clear interrupt flags of DMA2 stream 0 (SPI1_RX)  */
    DMA2->LIFCR = DMA_LIFCR_CDMEIF0
                | DMA_LIFCR_CFEIF0
                | DMA_LIFCR_CHTIF0
                | DMA_LIFCR_CTEIF0
                | DMA_LIFCR_CTCIF0;

    /* Set up RX DMA channel */
    DMA2_Stream0->NDTR = length;
    DMA2_Stream0->PAR = (uint32_t)&SPI1->DR;
    DMA2_Stream0->M0AR = (uint32_t)ptr;

    DMA2_Stream0->CR = (3 << DMA_SxCR_CHSEL_Pos)  // DMA channel 3 selects SPI1_RX request
                     | (1 << DMA_SxCR_MBURST_Pos) // 4-byte transfer (memory)
                     | (0 << DMA_SxCR_PBURST_Pos) // single transfer (peripheral)
                     | (0 << DMA_SxCR_MSIZE_Pos)  // mem data size = byte
                     | (0 << DMA_SxCR_PSIZE_Pos)  // periph data size = byte
                     | (1 << DMA_SxCR_MINC_Pos)   // increment memory address
                     | (0 << DMA_SxCR_PINC_Pos)   // do not increment peripheral address
                     | (0 << DMA_SxCR_DIR_Pos)    // direction: peripheral to memory
                     | (1 << DMA_SxCR_PFCTRL_Pos) // flow governed by peripheral
                     | (1 << DMA_SxCR_EN_Pos);    // enable stream

    /* Enable RX FIFO DMA */
    BITBAND(SPI1->CR2, SPI_CR2_RXDMAEN_Pos) = 1;

    /* Write <length> bytes into TX FIFO */
    // FIXME: Any value in doing this using DMA too?
    while (txlen > 0) {
      while (txlen > 0 && BITBAND(SPI1->SR, SPI_SR_TXE_Pos)) {
        txlen--;
        SPI1->DR = 0xff;
      }
    }

    /* Wait until DMA channel disables itself */
    while (!(DMA2->LISR & DMA_LISR_TCIF0));

    /* Disable RX FIFO DMA */
    BITBAND(SPI1->CR2, SPI_CR2_RXDMAEN_Pos) = 0;
  }
}

/* C19 boot-only fixed-block full-duplex DMA. No live-game call sites. */
static uint8_t gbc_dma_payload(const uint8_t *tx,uint8_t *rx) {
  const uint32_t flags=DMA_LISR_TCIF0|DMA_LISR_TCIF3;
  const uint32_t errors=DMA_LISR_TEIF0|DMA_LISR_DMEIF0|DMA_LISR_TEIF3|DMA_LISR_DMEIF3;
  const uint32_t clear=DMA_LIFCR_CTCIF0|DMA_LIFCR_CHTIF0|DMA_LIFCR_CTEIF0|DMA_LIFCR_CDMEIF0|DMA_LIFCR_CFEIF0|
                       DMA_LIFCR_CTCIF3|DMA_LIFCR_CHTIF3|DMA_LIFCR_CTEIF3|DMA_LIFCR_CDMEIF3|DMA_LIFCR_CFEIF3;
  if((DMA2_Stream0->CR|DMA2_Stream3->CR)&DMA_SxCR_EN)return 0;
  uint32_t cr2=SPI1->CR2;
  if(cr2&(SPI_CR2_RXDMAEN|SPI_CR2_TXDMAEN))return 0;
  uint32_t rcr=DMA2_Stream0->CR,tcr=DMA2_Stream3->CR,rfcr=DMA2_Stream0->FCR,tfcr=DMA2_Stream3->FCR;
  uint8_t ok=0;unsigned limit=1000000;tick_t start=getticks();
  /* Discard the command reply and clear any pre-existing overrun. */
  (void)SPI1->DR;(void)SPI1->SR;
  DMA2->LIFCR=clear;
  DMA2_Stream0->PAR=(uint32_t)&SPI1->DR;DMA2_Stream0->M0AR=(uint32_t)rx;DMA2_Stream0->NDTR=512;
  DMA2_Stream3->PAR=(uint32_t)&SPI1->DR;DMA2_Stream3->M0AR=(uint32_t)tx;DMA2_Stream3->NDTR=512;
  DMA2_Stream0->FCR=0;DMA2_Stream3->FCR=0;
  DMA2_Stream0->CR=(3u<<DMA_SxCR_CHSEL_Pos)|(3u<<DMA_SxCR_PL_Pos)|DMA_SxCR_MINC;
  DMA2_Stream3->CR=(3u<<DMA_SxCR_CHSEL_Pos)|(2u<<DMA_SxCR_PL_Pos)|DMA_SxCR_MINC|DMA_SxCR_DIR_0;
  __DMB();DMA2_Stream0->CR|=DMA_SxCR_EN;DMA2_Stream3->CR|=DMA_SxCR_EN;
  SPI1->CR2=cr2|SPI_CR2_RXDMAEN|SPI_CR2_TXDMAEN;
  while(limit--&&(tick_t)(getticks()-start)<MS_TO_TICKS(250)) {
    uint32_t state=DMA2->LISR;
    if((state&errors)||(SPI1->SR&SPI_SR_OVR))break;
    if((state&flags)==flags&&DMA2_Stream0->NDTR==0&&DMA2_Stream3->NDTR==0) {ok=1;break;}
  }
  SPI1->CR2=cr2;
  DMA2_Stream0->CR&=~DMA_SxCR_EN;DMA2_Stream3->CR&=~DMA_SxCR_EN;
  for(limit=100000;limit&&((DMA2_Stream0->CR|DMA2_Stream3->CR)&DMA_SxCR_EN);limit--);
  if(!limit)ok=0;
  for(limit=100000;limit&&(SPI1->SR&SPI_SR_BSY);limit--);
  if(!limit)ok=0;
  if(!ok) {
    /* Abort a partial SPI frame before the caller deasserts CS. */
    uint32_t cr1=SPI1->CR1;SPI1->CR1=cr1&~SPI_CR1_SPE;
    (void)SPI1->DR;(void)SPI1->SR;SPI1->CR1=cr1;
  }
  if(!((DMA2_Stream0->CR|DMA2_Stream3->CR)&DMA_SxCR_EN)) {
    DMA2_Stream0->CR=rcr;DMA2_Stream3->CR=tcr;DMA2_Stream0->FCR=rfcr;DMA2_Stream3->FCR=tfcr;
  }
  DMA2->LIFCR=clear;__DMB();return ok;
}
static uint8_t gbc_duplex_status(void) {
  FPGA_SELECT();FPGA_TX_BYTE(0xd3);uint8_t v=FPGA_RX_BYTE();FPGA_DESELECT();return v;
}
uint8_t spi_gbc_duplex_begin(void) {
  if(!gbc_spi_pacing)return 0;
  FPGA_SELECT();FPGA_TX_BYTE(0xd4);uint8_t v=FPGA_RX_BYTE();FPGA_DESELECT();
  if(v!=0xdf)return 0;
  FPGA_SELECT();FPGA_TX_BYTE(0xd0);FPGA_DESELECT();return gbc_duplex_status()==0xc0;
}
uint8_t spi_gbc_duplex_block(uint8_t command,const uint8_t *tx,uint8_t *rx) {
  if(!gbc_spi_pacing||(command!=0xd1&&command!=0xd2))return 0;
  FPGA_SELECT();FPGA_TX_BYTE(command);
  tick_t start=getticks();unsigned limit=1000000;
  while(!BITBAND(FPGA_MCU_RDY_REG->GPIO_I,FPGA_MCU_RDY_BIT)) {
    if(!limit--||(tick_t)(getticks()-start)>=MS_TO_TICKS(250)) {FPGA_DESELECT_ASYNC();return 0;}
  }
  /* Arm falling-edge FPGA MISO only after its first read words are ready. */
  FPGA_TX_BYTE(0);
  if(!gbc_dma_payload(tx,rx)) {FPGA_DESELECT_ASYNC();return 0;}
  FPGA_DESELECT();
  start=getticks();limit=10000;
  do {
    uint8_t v=gbc_duplex_status();if(v==0xc0)return 1;if(v!=0xc2)return 0;
  } while(--limit&&(tick_t)(getticks()-start)<MS_TO_TICKS(250));
  return 0;
}
/* C19 DMA end */
