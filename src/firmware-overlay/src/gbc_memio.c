#include "config.h"
#include "gbc_memio.h"
#include "fpga_spi.h"
#include "timer.h"
static uint32_t failed_address=0xffffffffu;
void gbc_memio_clear_error(void){failed_address=0xffffffffu;}
uint32_t gbc_memio_error_address(void){return failed_address;}
/* Unlike FPGA_WAIT_RDY, a diagnostic/state transaction must be abortable. */
static int wait_ready(uint32_t address){
 FPGA_TX_SYNC();delay_us(1); /* byte toggle/READY propagation into core clock */
 tick_t start=getticks();
 while(!BITBAND(FPGA_MCU_RDY_REG->GPIO_I,FPGA_MCU_RDY_BIT)){
  if((tick_t)(getticks()-start)>=MS_TO_TICKS(20)){
   if(failed_address==0xffffffffu)failed_address=address;
   return 0;
  }
 }
 return 1;
}
static int address_set(uint32_t address){
 FPGA_SELECT();
 if(!wait_ready(address)){FPGA_DESELECT();return 0;}
 FPGA_TX_BYTE(0);FPGA_TX_BYTE(address>>16);FPGA_TX_BYTE(address>>8);FPGA_TX_BYTE(address);
 FPGA_DESELECT();return 1;
}
uint16_t gbc_sram_readblock(void *buf,uint32_t addr,uint16_t size){
 uint8_t *out=buf;uint16_t done=0;
 if(!size)return 0;
 /* The decoder starts another read on every received dummy byte, including
  * the last. Burst only size-1 bytes, then read the tail without increment.
  * The final speculative read repeats a valid address, never crosses F0/F1
  * reset domains or a hole between state registers/palettes/OAM. */
 if(size>1){
  if(!address_set(addr))return 0;
  FPGA_SELECT();FPGA_TX_BYTE(0x88);
  while(done<size-1){
   if(!wait_ready(addr+done)){FPGA_DESELECT();return done;}
   out[done++]=FPGA_RX_BYTE();
  }
  if(!wait_ready(addr+done)){FPGA_DESELECT();return 0;}
  FPGA_DESELECT();
 }
 if(!address_set(addr+done))return done;
 FPGA_SELECT();FPGA_TX_BYTE(0x80);
 if(!wait_ready(addr+done)){FPGA_DESELECT();return done;}
 out[done]=FPGA_RX_BYTE();
 if(!wait_ready(addr+done)){FPGA_DESELECT();return done;}
 FPGA_DESELECT();return size;
}
uint16_t gbc_sram_writeblock(void *buf,uint32_t addr,uint16_t size){
 uint8_t *in=buf;uint16_t done=0;
 if(!size||!address_set(addr))return 0;
 FPGA_SELECT();FPGA_TX_BYTE(0x98);
 while(done<size){
  FPGA_TX_BYTE(in[done]);
  if(!wait_ready(addr+done)){FPGA_DESELECT();return done;}
  done++;
 }
 FPGA_DESELECT();return size;
}
