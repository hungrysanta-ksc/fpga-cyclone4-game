/* SPDX-License-Identifier: MIT */
/* Production SPI/TIM2 helpers, register side effects are modeled. */
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include "nes_menu_return.h"
typedef struct {uint32_t SR,DR,CNT,CR1,GPIO_I;} Reg;
static Reg spi,tim;
#define SPI1 (&spi)
#define TIM2 (&tim)
#define FPGA_MCU_RDY_REG (&gpio)
#define FPGA_MCU_RDY_BIT 4
#define SPI_SR_BSY_Pos 0
#define SPI_SR_TXE_Pos 1
#define SPI_SR_RXNE_Pos 2
#define TIM_SR_UIF_Pos 3
#define TIM_CR1_URS 4u
#define TIM_CR1_DIR 8u
#define TIM_CR1_CEN 1u
#define CONFIG_CPU_FREQUENCY 84000000u
static unsigned bits[5],read_calls,mode;static uint32_t ticks,step;
static unsigned *bit(unsigned pin){
 read_calls++;
 if(mode==1&&pin==3&&tim.CR1&&read_calls>5)bits[3]=1;
 if(mode==2&&pin==2)bits[2]=read_calls>6;
 return bits+pin;
}
#define BITBAND(reg,pin) (*bit(pin))
uint32_t nes_diag_ticks(void){ticks+=step;return ticks;}
bool nes_diag_sd_failed(void){return false;}
void nes_diag_observe(const struct nes_diag_report *r,bool a){(void)r;(void)a;}
#include "nes_return_spi.inc"
#include "nes_return_timer.inc"
static void setup(void){for(unsigned i=0;i<5;i++)bits[i]=0;spi=(Reg){0};tim=(Reg){0};ticks=step=read_calls=mode=0;nes_return_reset();nes_diag_begin();}
int main(void){unsigned cases=0;
 setup();bits[1]=bits[4]=1;assert(nes_return_spi_ready());cases++;
 for(unsigned n=0;n<5;n++){
  setup();bits[0]=n==0;bits[1]=n!=1;bits[2]=n==2;bits[4]=n!=3;
  step=n==4?0:1;ticks=UINT32_MAX-5;
  if(n==3)assert(!nes_return_spi_ready());else assert(!nes_return_spi_exchange(0x52));
  assert(nes_return_failed()&&nes_diag_status()->error==NES_DIAG_SPI&&read_calls<1000010);cases++;
 }
 setup();bits[1]=1;mode=2;assert(nes_return_spi_exchange(0x51)==0x51&&!nes_return_failed());cases++;
 setup();mode=1;bits[3]=1;assert(nes_return_delay(1,false)&&read_calls>5&&tim.CNT==84&&!tim.CR1&&!bits[3]);cases++;
 for(unsigned n=0;n<3;n++){
  setup();step=n?0:1;ticks=UINT32_MAX-1;bits[3]=1;
  assert(!nes_return_delay(n==2?UINT32_MAX:1,n==2));
  assert(nes_return_failed()&&nes_diag_status()->error==NES_DIAG_TIMER&&!tim.CR1&&read_calls<100100);cases++;
 }
 setup();nes_return_fail(NES_DIAG_SPI);assert(!nes_return_delay(1,true)&&!nes_return_spi_ready()&&!read_calls);cases++;
 printf("PASS MENU065 wait cases=%u SPI_frozen_tick=1 TIM2_stale_flag=1 wrap=1\n",cases);
 return 0;
}
