/* SPDX-License-Identifier: MIT */
/* Execute the production engine with a register model, including delayed flags.
 * Not a cycle-accurate STM32 model or physical guard-latency measurement. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
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
#define RCC_CFGR_HPRE 0xf0u
#define RCC_CFGR_PPRE2 0xe000u
static struct {uint32_t CR1,CR2,SR,DR;} spi;
static struct {uint32_t MODER,AFR[2],BSRR;} gpio;
static struct {uint32_t CFGR;} rcc;
#define SPI1 (&spi)
#define GPIOB (&gpio)
#define RCC (&rcc)
static bool gpio_owned=true,failed,selected,monitoring=true;
static unsigned writes,reads,polls,guard_checks,inject_check,delay_count,pending_polls;
static int stuck;static uint32_t injected_error;static unsigned error_byte;
static uint8_t sent[8],received[8];
static bool nes_cf86_monitoring094(void){return monitoring;}
static bool nes_cf86_fail094(void){failed=true;return false;}
static bool nes_cf86_check094(void){
 guard_checks++;
 if(inject_check&&guard_checks==inject_check)failed=true;
 return !failed;
}
static uint32_t sr149(void){
 polls++;
 if(writes==error_byte)spi.SR|=injected_error;
 if(pending_polls&&--pending_polls==0) {
  if(stuck!=2)spi.SR|=SPI_SR_RXNE;
  if(stuck!=3)spi.SR&=~SPI_SR_BSY;
 }
 return spi.SR;
}
static void write149(uint8_t b){
 assert(selected&&(spi.CR1&SPI_CR1_SPE)&&writes<8);
 assert(((spi.CR1>>SPI_CR1_BR_Pos)&7)==4);
 assert(!pending_polls);sent[writes]=b;received[writes]=(uint8_t)(b^0x96);
 spi.DR=received[writes++];spi.SR=SPI_SR_TXE|SPI_SR_BSY;pending_polls=3;
}
static uint8_t read149(void){
 uint8_t b=spi.DR;
 if(selected){assert(spi.SR&SPI_SR_RXNE);reads++;}
 spi.SR&=~(SPI_SR_RXNE|SPI_SR_OVR);return b;
}
#define NES149_SR() sr149()
#define NES149_READ() read149()
#define NES149_WRITE(v) write149(v)
#include "nes_game149_spi.inc"
static void select149(void *ctx,bool v){(void)ctx;selected=v;}
static void wait149(void *ctx,unsigned us){(void)ctx;assert(us==2);delay_count++;}
static const struct nes_rom_spi_io io={0,select149,0,0,0,wait149};
static void reset149(void){
 spi.CR1=0x304;spi.CR2=0;spi.SR=SPI_SR_TXE;spi.DR=0;
 gpio.MODER=0xa5000000|NES149_GPIO_MODE;gpio.AFR[0]=0x00555000;rcc.CFGR=0;
 writes=reads=polls=guard_checks=inject_check=delay_count=pending_polls=0;
 stuck=0;injected_error=0;error_byte=1;failed=selected=false;gpio_owned=monitoring=true;
}
static void stopped(void){
 assert(!selected&&!(spi.CR1&SPI_CR1_SPE));
 assert(gpio.MODER==(0xa5000000|NES149_GPIO_MODE));
 assert(spi.CR1==0x304&&spi.CR2==0);
}
int main(void){
 const uint8_t tx[8]={0x65,0x06,0,0,0xa5,0x5a,0xff,1};uint8_t rx[8];unsigned cases=0;
 reset149();assert(nes_game149_transfer(&io,tx,rx));stopped();
 assert(writes==8&&reads==8&&memcmp(tx,sent,8)==0&&memcmp(rx,received,8)==0&&delay_count==4);
 unsigned normal_checks=guard_checks;cases++;
 /* Shared-fault injection at EVERY executed normal guard position. */
 for(unsigned i=1;i<=normal_checks;i++){
  reset149();inject_check=i;assert(!nes_game149_transfer(&io,tx,rx));assert(failed);stopped();
  unsigned before=writes;assert(!nes_game149_transfer(&io,tx,rx));assert(writes==before);cases++;
 }
 for(int mode=1;mode<=3;mode++){
  reset149();stuck=mode;if(mode==1)spi.SR=0;
  assert(!nes_game149_transfer(&io,tx,rx));assert(failed&&polls<600);stopped();cases++;
 }
 const uint32_t errors[]={SPI_SR_OVR,SPI_SR_MODF,SPI_SR_CRCERR,SPI_SR_FRE};
 for(unsigned b=1;b<=8;b++)for(unsigned e=0;e<4;e++){
  reset149();error_byte=b;injected_error=errors[e];assert(!nes_game149_transfer(&io,tx,rx));
  assert(failed&&writes==b);stopped();cases++;
 }
 reset149();spi.SR|=SPI_SR_RXNE|SPI_SR_OVR;assert(nes_game149_transfer(&io,tx,rx));stopped();cases++;
 reset149();spi.CR2=1;assert(!nes_game149_transfer(&io,tx,rx)&&!writes&&failed);cases++;
 reset149();gpio.AFR[0]=0;assert(!nes_game149_transfer(&io,tx,rx)&&!writes&&failed);cases++;
 reset149();rcc.CFGR=RCC_CFGR_PPRE2;assert(!nes_game149_transfer(&io,tx,rx)&&!writes&&failed);cases++;
 reset149();gpio_owned=false;assert(!nes_game149_transfer(&io,tx,rx)&&!writes);cases++;
 reset149();monitoring=false;assert(!nes_game149_transfer(&io,tx,rx)&&!writes);cases++;
 printf("PASS149 transport cases=%u normal_guard_checks=%u bytes=8 errors=4 stuck=3\n",cases,normal_checks);
 return 0;
}
