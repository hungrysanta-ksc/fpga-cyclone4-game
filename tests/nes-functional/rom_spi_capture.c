/* SPDX-License-Identifier: MIT */
/* Independent expected status model. Replay all actual C callback pin/sample
 * times in RTL; the model alone is not an integration pass. */
#include "nes_rom_spi.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static FILE *wave;
static unsigned long long ns,previous;
static unsigned ss=1,sck,mosi,bit,samples,frames,count;
static unsigned flags,protocol_error,loader_error;
static uint8_t tx[8],reply[8];
static void record(int expect){fprintf(wave,"%llu %u %u %u %d\n",ns-previous,ss,sck,mosi,expect);previous=ns;}
static void select_pin(void *ctx,bool active){
 (void)ctx;ss=!active;record(-1);
 if(active){bit=0;memset(tx,0,sizeof(tx));memset(reply,0,sizeof(reply));}
 else{
  assert(bit==64);frames++;
  unsigned offset=((unsigned)tx[1]<<16)|((unsigned)tx[2]<<8)|tx[3];
  uint8_t check[8];nes_rom_spi_frame(check,tx[0],offset,tx[4]);
  if(protocol_error)return;
  if(memcmp(check,tx,8)){protocol_error=2;flags=(flags&0x10)|8;return;}
  if(tx[0]==NES_ROM_STATUS)return;
  if(tx[0]!=NES_ROM_BEGIN&&offset!=count){protocol_error=5;flags=8;return;}
  switch(tx[0]){
   case NES_ROM_BEGIN:count=0;flags=1;break;
   case NES_ROM_DATA:assert(flags==1);count++;break;
   case NES_ROM_STOP:count=0;flags=0;break;
   case NES_ROM_START:loader_error=3;flags=0x10;break;
   default:assert(0);
  }
 }
}
static void clock_pin(void *ctx,bool high){
 (void)ctx;sck=high;record(-1);
 if(high){
  assert(bit<64);tx[bit/8]=(uint8_t)((tx[bit/8]<<1)|mosi);bit++;
  if(bit==8){reply[1]=0x54;reply[2]=(uint8_t)flags;reply[3]=(uint8_t)protocol_error;
   reply[4]=(uint8_t)(count>>16);reply[5]=(uint8_t)(count>>8);reply[6]=(uint8_t)count;reply[7]=(uint8_t)loader_error;}
 }
}
static void mosi_pin(void *ctx,bool high){(void)ctx;mosi=high;record(-1);}
static bool miso_pin(void *ctx){
 (void)ctx;assert(bit>0);unsigned b=bit-1;int expected=(reply[b/8]>>(7-b%8))&1;
 record(b<8?-2:expected);samples++;return expected!=0;
}
static void wait_us(void *ctx,unsigned delay){(void)ctx;ns+=(unsigned long long)delay*1000;}
int main(int argc,char **argv){
 assert(argc==2);wave=fopen(argv[1],"w");assert(wave);
 struct nes_rom_spi_io io={0,select_pin,clock_pin,mosi_pin,miso_pin,wait_us};
 struct nes_rom_spi_status status;
 assert(nes_rom_spi_query(&io,&status)&&status.count==0&&status.flags==0);
 assert(nes_rom_spi_command(&io,NES_ROM_BEGIN,0,1,&status));
 for(unsigned i=0;i<64;i++)assert(nes_rom_spi_command(&io,NES_ROM_DATA,i,(uint8_t)(i^0xa5),&status));
 assert(status.count==64);
 assert(nes_rom_spi_command(&io,NES_ROM_STOP,64,0,&status)&&status.count==0);
 assert(nes_rom_spi_command(&io,NES_ROM_BEGIN,0,0,&status));
 uint8_t bad[8],rx[8];nes_rom_spi_frame(bad,NES_ROM_DATA,0,0x99);bad[6]^=1;
 assert(nes_rom_spi_transfer(&io,bad,rx));
 assert(!nes_rom_spi_query(&io,&status)&&status.protocol_error==2&&status.count==0);
 assert(!nes_rom_spi_command(&io,NES_ROM_DATA,0,0x99,&status));
 unsigned before=frames;
 assert(!nes_rom_spi_command(&io,NES_ROM_BEGIN,1,0,&status));
 assert(!nes_rom_spi_command(&io,NES_ROM_START,0,1,&status));
 assert(!nes_rom_spi_command(&io,NES_ROM_BEGIN,0,0,0));
 assert(frames==before);
 fclose(wave);printf("PASS MCU SPI frames=%u samples=%u payload=64 crc_negative=1\n",frames,samples);return 0;
}
