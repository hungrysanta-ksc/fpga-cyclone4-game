/* SPDX-License-Identifier: MIT */
#include "nes_rom_spi.h"
#include <stddef.h>
void nes_rom_spi_frame(uint8_t out[8],uint8_t command,uint32_t offset,uint8_t arg) {
 out[0]=command;out[1]=(uint8_t)(offset>>16);out[2]=(uint8_t)(offset>>8);out[3]=(uint8_t)offset;
 out[4]=arg;out[5]=(uint8_t)~arg;uint8_t crc=0;
 for(unsigned i=0;i<6;i++){crc^=out[i];for(unsigned b=0;b<8;b++)crc=(uint8_t)((crc<<1)^((crc&0x80)?7:0));}
 out[6]=crc;out[7]=0xa5;
}
bool nes_rom_spi_transfer(const struct nes_rom_spi_io *io,const uint8_t tx[8],uint8_t rx[8]) {
 if(!io||!tx||!rx||!io->select||!io->clock||!io->mosi||!io->miso||!io->wait_us)return false;
 io->clock(io->ctx,false);io->select(io->ctx,true);io->wait_us(io->ctx,2);
 for(unsigned i=0;i<8;i++){
  uint8_t value=0;
  for(unsigned b=0;b<8;b++){
   io->mosi(io->ctx,(tx[i]&(0x80u>>b))!=0);io->wait_us(io->ctx,2);
   io->clock(io->ctx,true);io->wait_us(io->ctx,2);
   value=(uint8_t)((value<<1)|io->miso(io->ctx));io->clock(io->ctx,false);
  }
  rx[i]=value;io->wait_us(io->ctx,2);
 }
 io->wait_us(io->ctx,2);io->select(io->ctx,false);io->wait_us(io->ctx,2);
 return true;
}
bool nes_rom_spi_query(const struct nes_rom_spi_io *io,struct nes_rom_spi_status *s) {
 uint8_t tx[8],rx[8];if(!s)return false;
 nes_rom_spi_frame(tx,NES_ROM_STATUS,0,0);
 if(!nes_rom_spi_transfer(io,tx,rx)||rx[1]!=0x54||(rx[4]&0xfe)||(rx[2]&0xe0))return false;
 s->flags=rx[2];s->protocol_error=rx[3];s->count=((uint32_t)rx[4]<<16)|((uint32_t)rx[5]<<8)|rx[6];s->loader_error=rx[7];
 return s->count<=0x18000&&!(s->flags&0x18)&&!s->protocol_error&&!s->loader_error;
}
bool nes_rom_spi_command(const struct nes_rom_spi_io *io,uint8_t command,uint32_t offset,uint8_t arg,struct nes_rom_spi_status *s) {
 if(!s||command<NES_ROM_BEGIN||command>NES_ROM_STOP||offset>0x18000||
    (command==NES_ROM_BEGIN?(offset!=0||arg>1):(command!=NES_ROM_DATA&&arg!=0)))return false;
 uint8_t tx[8],rx[8];nes_rom_spi_frame(tx,command,offset,arg);
 // A transaction replies with the pre-command snapshot. Query AFTER SS commit.
 if(!nes_rom_spi_transfer(io,tx,rx)||!nes_rom_spi_query(io,s))return false;
 switch(command){
  case NES_ROM_BEGIN:return s->count==0&&(s->flags&7)==1;
  case NES_ROM_DATA:return s->count==offset+1&&!(s->flags&6);
  case NES_ROM_END:return s->count==offset&&(s->flags&7)==2;
  case NES_ROM_START:return s->count==offset&&(s->flags&7)==6;
  case NES_ROM_STOP:return (s->flags==0&&s->count==0)||(s->flags==2&&s->count==offset);
  default:return false;
 }
}
