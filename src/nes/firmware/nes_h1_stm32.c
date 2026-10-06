/* SPDX-License-Identifier: MIT */
#include <string.h>
#include "config.h"
#include "bits.h"
#include "timer.h"
#include "snes.h"
#include "fpga.h"
#include "fpga_spi.h"
#include "fileops.h"
#include "uart.h"
#include "nes_h1_session.h"
#include "nes_h1_stm32.h"

/* Existing fpga.c function omitted from the upstream public header. */
extern int fpga_get_done(void);

#define H1_MODE_MASK ((3u<<6)|(3u<<8)|(3u<<10))
#define H1_OUT_MASK ((1u<<3)|(1u<<5))
static bool gpio_owned;
static uint32_t saved_mode, saved_output, saved_cr1;

bool nes_h1_is_marker(const uint8_t *path) {
 const char *ext=strrchr((const char *)path,'.');
 return ext && (ext[1]=='n'||ext[1]=='N') &&
   (ext[2]=='h'||ext[2]=='H') && ext[3]=='1' && ext[4]==0;
}

static bool slow_begin(void) {
 if(gpio_owned)return false;
 for(unsigned tries=0;SPI1->SR & SPI_SR_BSY;tries++) {
  if(tries==1000)return false;
  delay_us(1);
 }
 saved_cr1=SPI1->CR1;
 saved_mode=GPIOB->MODER & H1_MODE_MASK;
 saved_output=GPIOB->ODR & H1_OUT_MASK;
 SET_BIT(FPGA_SSREG,FPGA_SSBIT);
 SPI1->CR1=saved_cr1 & ~SPI_CR1_SPE;
 CLEAR_BIT(GPIOB,3);
 CLEAR_BIT(GPIOB,5);
 /* PB3 SCK/PB5 MOSI output, PB4 MISO input. Leave AF, speed and pulls alone. */
 GPIOB->MODER=(GPIOB->MODER & ~H1_MODE_MASK)|(1u<<6)|(1u<<10);
 gpio_owned=true;
 delay_us(2);
 return true;
}

static void slow_end(void) {
 if(!gpio_owned)return;
 SET_BIT(FPGA_SSREG,FPGA_SSBIT);
 CLEAR_BIT(GPIOB,3);
 if(saved_output & (1u<<3))SET_BIT(GPIOB,3);
 if(saved_output & (1u<<5))SET_BIT(GPIOB,5);else CLEAR_BIT(GPIOB,5);
 GPIOB->MODER=(GPIOB->MODER & ~H1_MODE_MASK)|saved_mode;
 SPI1->CR1=saved_cr1;
 gpio_owned=false;
}

static bool slow_transaction(void *ctx,const uint8_t *tx,uint8_t *rx,size_t n) {
 (void)ctx;
 if(!gpio_owned || n<1 || n>3)return false;
 CLEAR_BIT(GPIOB,3);
 CLEAR_BIT(FPGA_SSREG,FPGA_SSBIT);
 delay_us(2);
 for(size_t i=0;i<n;i++) {
  uint8_t value=0;
  for(unsigned bit=0;bit<8;bit++) {
   if(tx[i] & (0x80u>>bit))SET_BIT(GPIOB,5);else CLEAR_BIT(GPIOB,5);
   delay_us(2);
   SET_BIT(GPIOB,3);
   delay_us(2);
   value=(uint8_t)((value<<1)|((GPIOB->IDR>>4)&1u));
   CLEAR_BIT(GPIOB,3);
  }
  rx[i]=value;
  delay_us(2);
 }
 delay_us(2);
 SET_BIT(FPGA_SSREG,FPGA_SSBIT);
 delay_us(2);
 return true;
}

static void reset_cpu(void *ctx,bool asserted) {
 (void)ctx;snes_reset(asserted?1:0);
}
static void wait_us(void *ctx,unsigned duration) {
 (void)ctx;delay_us(duration);
}
static bool configured(const char *image) {
 return file_res==FR_OK && fpga_get_done() && fpga_config &&
   strcmp((const char *)fpga_config,image)==0;
}
static bool configure_h1(void *ctx,const char *image) {
 (void)ctx;
 fpga_pgm((uint8_t *)image);
 return configured(image) && slow_begin();
}

bool nes_h1_run(void) {
 const struct nes_h1_io io={0,reset_cpu,configure_h1,slow_transaction,wait_us};
 /* USB CDC IN interrupts can call usbint_handler_dat() and stock SPI.
  * Quiesce that single IRQ across reconfiguration and H1 ownership.
  * SysTick/SD interrupts stay enabled; preserve a previously disabled USB IRQ. */
 bool usb_irq_enabled=NVIC_GetEnableIRQ(OTG_FS_IRQn)!=0;
 NVIC_DisableIRQ(OTG_FS_IRQn);
 uint16_t epoch=0;
 enum nes_h1_result result=nes_h1_start(&io,&epoch);
 printf("H1 start=%u epoch=%u\n",(unsigned)result,(unsigned)epoch);
 if(result==NES_H1_OK) {
  /* Allow our released RESET line to settle; do not use stock reset handler,
   * save-RAM routines or high-speed SPI while the diagnostic is loaded. */
  delay_ms(1);
  for(;;) {
   uint8_t tx[2]={0xf2,0},rx[2]={0,0};
   if(get_snes_reset())break;
   if(!slow_transaction(0,tx,rx,2) || rx[1]!=3) {
    printf("H1 status fault=%u\n",(unsigned)rx[1]);break;
   }
   delay_ms(1);
  }
 }
 snes_reset(1);
 if(gpio_owned) {
  result=nes_h1_stop(&io);
  printf("H1 stop=%u\n",(unsigned)result);
 }
 slow_end();
 /* Reload unconditionally, including a failed H1 configure. Keep RESET held.
  * Stock loader can enter led_panic on configuration hardware faults. */
 fpga_pgm((uint8_t *)FPGA_BASE);
 if(!configured((const char *)FPGA_BASE))return false;
 /* Do not enter the stock blocking SPI routine if takeover found a fault. */
 if((SPI1->SR & SPI_SR_BSY) || !(SPI1->SR & SPI_SR_TXE))return false;
 if(fpga_test()!=FPGA_TEST_TOKEN)return false;
 if(usb_irq_enabled)NVIC_EnableIRQ(OTG_FS_IRQn);
 return true;
}
