/* SPDX-License-Identifier: MIT */
/* APB sample/byte shift model, not MCU instruction, RTL or pad timing. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <setjmp.h>
#include "nes_diag_runtime.h"
#include "cmsis101.h"
static unsigned clock101,reads101,writes101,completed101,cs101=1;
static unsigned queued101,delay101,shift101,queued_byte101,active_byte101,rx101,reply101;
static unsigned start_delay101=2,byte_cycles101=16,fault101,frozen101,legacy101,fast101;
static unsigned spe101=1,af101=5,reset101,irq101=1;
static jmp_buf blocked101;
uint32_t nes_diag_ticks(void){return frozen101?0:clock101/(fast101?1:100);}
void nes_diag_observe(const struct nes_diag_report *r,bool a){(void)r;(void)a;}
bool nes_diag_sd_failed(void){return false;}
bool nes_return_failed(void);
void nes_return_fail(enum nes_diag_error);
static unsigned status_bit101(unsigned pin){
 unsigned flags=(!queued101?SPI_SR_TXE:0)|(shift101?SPI_SR_BSY:0)|(rx101?SPI_SR_RXNE:0);
 if(fault101==1)flags&=~SPI_SR_TXE;
 if(fault101==2)flags|=SPI_SR_BSY;
 if(fault101==3)flags&=~SPI_SR_RXNE;
 reads101++;clock101++;
 if(!fault101){
  if(shift101&&!--shift101){completed101++;rx101=1;reply101=active_byte101^0xa5;printf("DONE cycle=%u byte=%02x\n",clock101,active_byte101);}
  if(!shift101&&queued101){
   if(delay101)delay101--;
   else{queued101=0;shift101=byte_cycles101;active_byte101=queued_byte101;printf("START cycle=%u byte=%02x\n",clock101,active_byte101);}
  }
 }
 assert(reads101<1100000);return !!(flags&(1u<<pin));
}
static void write_dr101(unsigned v){assert(!cs101&&!queued101);writes101++;queued101=1;delay101=start_delay101;queued_byte101=v&255;printf("DR cycle=%u byte=%02x\n",clock101,v&255);}
static unsigned read_dr101(void){assert(rx101);rx101=0;return reply101;}
static void cs_pin101(unsigned p,unsigned b,unsigned high){
 (void)p;(void)b;
 printf("CS cycle=%u high=%u queued=%u shifting=%u error=%u\n",clock101,high,queued101,shift101,nes_diag_status()->error);
 if(high&&!nes_return_failed())assert(!queued101&&!shift101);
 cs101=high;
}
static void gbc_spi_byte_gap(void){assert(legacy101);}
static unsigned gbc_spi_pacing;
#define BITBAND(r,p) status_bit101(p)
#define FPGA_SSREG 0
#define FPGA_SSBIT 4
#define SET_BIT(p,b) cs_pin101(p,b,1)
#define CLEAR_BIT(p,b) cs_pin101(p,b,0)
static void snes_reset(unsigned v){reset101=v;}
#define OTG_FS_IRQn 0
#define NVIC_DisableIRQ(n) ((void)(n),irq101=0)
#define __NOP() longjmp(blocked101,1)
#include "return101.inc"
#include "spi101.inc"
#include "select101.h"
#include "blocked101.inc"
int main(int argc,char **argv){
 setvbuf(stdout,NULL,_IONBF,0);
 assert(argc==5);unsigned test=atoi(argv[1]);start_delay101=atoi(argv[2]);byte_cycles101=atoi(argv[3]);unsigned offset=atoi(argv[4]);
 nes_diag_begin();nes_return_reset();nes_return_io_begin();FPGA_SELECT();
 if(test==0||test==1){
  spi_tx_byte(0x39);
  for(unsigned i=0;i<offset;i++)(void)status_bit101(SPI_SR_BSY_Pos);
  if(test==1){unsigned r=spi_txrx_byte(0x72);assert(r==(0x72^0xa5));}
  FPGA_DESELECT();assert(!nes_return_failed()&&cs101&&completed101==test+1&&writes101==test+1);
 }else if(test==2){
  for(unsigned i=0;i<257;i++)spi_tx_byte(i);
  FPGA_DESELECT();assert(!nes_return_failed()&&completed101==257&&cs101);
 }else if(test>=3&&test<=8){
  spi_tx_byte(0x39);fault101=(test-3)%3+1;frozen101=test>=6;
  if(fault101==3)(void)spi_txrx_byte(0x72);else spi_tx_sync();
  assert(nes_return_failed());unsigned before=reads101,w=writes101;
  FPGA_DESELECT();FPGA_SELECT();spi_tx_byte(0x77);assert(reads101==before&&writes101==w&&cs101);
 }else if(test==9){
  nes_return_fail(NES_DIAG_SD_CRC);unsigned before=reads101;
  spi_tx_sync();(void)spi_txrx_byte(0x33);assert(reads101==before&&writes101==0&&nes_diag_status()->error==NES_DIAG_SD_CRC);
 }else if(test==10){
  frozen101=1;fault101=1;nes_return_log_allow(true);spi_tx_sync();assert(nes_diag_status()->error==NES_DIAG_MENU);
 }else if(test==11){
  fast101=1;fault101=1;spi_tx_sync();assert(nes_diag_status()->error==NES_DIAG_SPI);
 }else if(test==12){
  /* Characterize the still-open abort boundary using the real blocked body. */
  spi_tx_byte(0x39);fault101=1;spi_tx_sync();assert(nes_return_failed()&&queued101);
  FPGA_DESELECT();if(!setjmp(blocked101))nes_diag_blocked();
  assert(reset101&&!irq101&&cs101&&spe101==1&&af101==5&&queued101);
  puts("OPEN101 blocked does not disable SPI or disconnect AF; queued byte not cancelled");
 }else if(test==13){
  nes_diag_leave();legacy101=1;spi_tx_byte(0x39);
  /* Established legacy path is unchanged; wait externally before sync. */
  for(unsigned i=0;i<64;i++)(void)status_bit101(SPI_SR_BSY_Pos);
  FPGA_DESELECT();assert(completed101==1&&cs101);
 }else abort();
 printf("PASS101 test=%u delay=%u cycles=%u offset=%u reads=%u writes=%u completed=%u error=%u\n",test,start_delay101,byte_cycles101,offset,reads101,writes101,completed101,nes_diag_status()->error);
 return 0;
}
