/* SPDX-License-Identifier: MIT */
/* Included by the materialized nes_h1_stm32.c after gpio_owned and io types.
 * STM32F401 RM0368: master/full-duplex completion is RXNE, then TXE/!BSY.
 * No DMA, no queued second byte, no retry of a possibly committed command.
 * Hardware clocks one byte autonomously; CF86 is checked on every status poll.
 * CSS/NMI remains the existing108 SPI-disable/reset fail-stop implementation.
 */
#ifndef NES149_SR
#include "nes_cf86_session094.h"
#if CONFIG_CPU_FREQUENCY != 84000000
#error "NES149 requires the verified 84MHz STM32 clock configuration"
#endif
#define NES149_SR() (SPI1->SR)
#define NES149_READ() (*(volatile uint8_t *)&SPI1->DR)
#define NES149_WRITE(v) (*(volatile uint8_t *)&SPI1->DR=(v))
#endif
#define NES149_MODE_MASK ((3u<<6)|(3u<<8)|(3u<<10))
#define NES149_GPIO_MODE ((1u<<6)|(1u<<10))
#define NES149_AF_MODE ((2u<<6)|(2u<<8)|(2u<<10))
#define NES149_ERRORS (SPI_SR_OVR|SPI_SR_MODF|SPI_SR_CRCERR|SPI_SR_FRE)

static bool nes149_wait(uint32_t mask,bool set) {
 for(unsigned i=0;i<512;i++) {
  if(!nes_cf86_check094())return false;
  uint32_t sr=NES149_SR();
  if(sr&NES149_ERRORS)return false;
  if(!!(sr&mask)==set)return true;
 }
 return false;
}

bool nes_game149_transfer(const struct nes_rom_spi_io *io,const uint8_t tx[8],uint8_t rx[8]) {
 if(!io||!tx||!rx||!io->select||!io->wait_us||!gpio_owned||
    !nes_cf86_monitoring094()||!nes_cf86_check094())return false;
 uint32_t cr1=SPI1->CR1,mode=GPIOB->MODER & NES149_MODE_MASK;
 /* Claim only the already quiesced GPIO owner; leave unrelated pins alone.
  * APB2=/1 at84MHz is part of this candidate's checked clock contract. */
 if((cr1&SPI_CR1_SPE)||SPI1->CR2||mode!=NES149_GPIO_MODE||
    (GPIOB->AFR[0]&0x00fff000u)!=0x00555000u||
    (RCC->CFGR&(RCC_CFGR_HPRE|RCC_CFGR_PPRE2))||
    (NES149_SR()&SPI_SR_BSY))return nes_cf86_fail094();
 /* Stock programming may leave discarded RX data/OVR. The peripheral is
  * disabled and idle: documented DR then SR clearing, never drain a live byte. */
 (void)NES149_READ();(void)NES149_SR();
 if(NES149_SR()&NES149_ERRORS)return nes_cf86_fail094();
 io->select(io->ctx,false);
 SPI1->CR1=SPI_CR1_MSTR|SPI_CR1_SSM|SPI_CR1_SSI|(4u<<SPI_CR1_BR_Pos);
 GPIOB->MODER=(GPIOB->MODER&~NES149_MODE_MASK)|NES149_AF_MODE;
 SPI1->CR1|=SPI_CR1_SPE;
 io->wait_us(io->ctx,2);
 if(!nes_cf86_check094())goto fail;
 io->select(io->ctx,true);io->wait_us(io->ctx,2);
 for(unsigned i=0;i<8;i++) {
  if(!nes149_wait(SPI_SR_TXE,true))goto fail;
  NES149_WRITE(tx[i]);
  if(!nes149_wait(SPI_SR_RXNE,true))goto fail;
  rx[i]=NES149_READ();
 }
 if(!nes149_wait(SPI_SR_TXE,true)||!nes149_wait(SPI_SR_BSY,false))goto fail;
 io->wait_us(io->ctx,2);
 if(!nes_cf86_check094())goto fail;
 io->select(io->ctx,false);io->wait_us(io->ctx,2);
 if(!nes_cf86_check094())goto fail;
 SPI1->CR1&=~SPI_CR1_SPE;
 GPIOB->MODER=(GPIOB->MODER&~NES149_MODE_MASK)|mode;
 SPI1->CR1=cr1; /* saved CR1 is disabled; slow_end owns stock restoration */
 return true;
fail:
 /* Abandon the frame before disconnecting the peripheral. Never resume it. */
 io->select(io->ctx,false);
 SPI1->CR1&=~SPI_CR1_SPE;
 GPIOB->BSRR=(1u<<(3+16))|(1u<<(5+16));
 GPIOB->MODER=(GPIOB->MODER&~NES149_MODE_MASK)|mode;
 SPI1->CR1=cr1;
 return nes_cf86_fail094();
}
