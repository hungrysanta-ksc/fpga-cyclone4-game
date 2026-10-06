/* SPDX-License-Identifier: MIT */
#include "nes_rom_verify.h"
#include <string.h>
enum {CHECK_OPEN=0x66,CHECK_READ=0x67,CHECK_ACK=0x68,CHECK_FINISH=0x69,CHECK_STATUS=0x6a};
static bool transfer(const struct nes_rom_spi_io *io,uint8_t op,uint32_t offset,uint8_t data,uint8_t rx[8]) {
 uint8_t tx[8];nes_rom_spi_frame(tx,op,offset,data);return nes_rom_spi_transfer(io,tx,rx);
}
static uint32_t number(const uint8_t rx[8]) {return ((uint32_t)rx[4]<<16)|((uint32_t)rx[5]<<8)|rx[6];}
static bool status(const struct nes_rom_spi_io *io,uint32_t length,uint8_t flags) {
 uint8_t rx[8];return transfer(io,NES_ROM_STATUS,0,0,rx)&&rx[1]==0x59&&rx[2]==flags&&
  rx[3]==0&&number(rx)==length&&rx[7]==0;
}
bool nes_rom_verify(const struct nes_rom_spi_io *io,uint32_t length,nes_verify_source source,void *ctx,struct nes_verify_report *r) {
 uint8_t rx[8],expected=0;bool opened=false;
 if(!r)return false;
 memset(r,0,sizeof(*r));
 if(!source||(length!=0x14000&&length!=0x18000)){r->error=NES_VERIFY_ARGUMENT;return false;}
 if(!status(io,length,2)){r->error=NES_VERIFY_PROTOCOL;return false;}
 opened=true; /* A lost response cannot prove OPEN was not committed. */
 if(!transfer(io,CHECK_OPEN,0,0,rx)||!status(io,length,0x22)){r->error=NES_VERIFY_PROTOCOL;goto fail;}
 for(uint32_t a=0;a<length;a++) {
  if(!source(ctx,a,&expected)){r->error=NES_VERIFY_SOURCE;goto fail;}
  if(!transfer(io,CHECK_READ,a,0,rx)){r->error=NES_VERIFY_IO;goto fail;}
  bool complete=false;
  for(unsigned poll=0;poll<4;poll++) {
   if(!transfer(io,CHECK_STATUS,0,0,rx)){r->error=NES_VERIFY_IO;goto fail;}
   if(rx[1]!=0x59||(rx[2]!=0x23&&rx[2]!=0x62)||rx[7]){r->error=NES_VERIFY_PROTOCOL;goto fail;}
   if(number(rx)!=a){r->error=NES_VERIFY_TAG;goto fail;}
   if(rx[2]==0x62){complete=true;break;}
  }
  if(!complete){r->error=NES_VERIFY_TIMEOUT;goto fail;}
  if(rx[3]!=expected){r->error=NES_VERIFY_DATA;goto fail;}
  if(!transfer(io,CHECK_ACK,a,expected,rx)){r->error=NES_VERIFY_IO;goto fail;}
  r->compared=a+1;
 }
 if(!transfer(io,CHECK_FINISH,length,0,rx)||!status(io,length,0x82)){r->error=NES_VERIFY_PROTOCOL;goto fail;}
 return true;
fail:
 if(opened && transfer(io,NES_ROM_STOP,length,0,rx))r->stop_ok=status(io,0,0);
 return false;
}
bool nes_rom_verified_start(const struct nes_rom_spi_io *io,uint32_t length) {
 uint8_t rx[8];
 return (length==0x14000||length==0x18000)&&status(io,length,0x82)&&
  transfer(io,NES_ROM_START,length,0,rx)&&status(io,length,0x86);
}
