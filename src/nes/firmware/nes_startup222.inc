/* SPDX-License-Identifier: MIT */
/* Probe bridge admission before RESET release. /WR can stay low in RESET,
 * so an undriven-looking reply defers admission to one post-release probe.
 * F7 shares the ROM lifetime; neither probe proves physical CPU execution.
 * No START replay, packet enqueue, timer extension, reset retry or SD IO. */
#include "nes_startup222.h"
static unsigned startup_probe222(const struct nes_rom_spi_io *io,uint8_t reply[20],bool held){
 uint8_t tx[20]={0xe0},crc=0;
 if(!!get_snes_reset()!=held||!nes_cf86_check094())return NES_STARTUP222_GUARD;
 if(!nes_native165_bulk(io,tx,reply,20))return NES_STARTUP222_IO;
 if(!!get_snes_reset()!=held||!nes_cf86_check094())return NES_STARTUP222_GUARD;
 bool zero=true,ones=true;
 for(unsigned i=1;i<20;i++){zero=zero&&reply[i]==0;ones=ones&&reply[i]==255;}
 if(zero||ones)return NES_STARTUP222_NO_RESPONSE;
 for(unsigned i=1;i<19;i++){
  crc^=reply[i];
  for(unsigned bit=0;bit<8;bit++)crc=(uint8_t)(crc&128?(crc<<1)^7:crc<<1);
 }
 if(reply[1]!=0xf7||reply[19]!=crc)return NES_STARTUP222_PROTOCOL;
 for(unsigned i=2;i<19;i++)if(reply[i])return NES_STARTUP222_NOT_EMPTY;
 return NES_STARTUP222_READY;
}
static bool native_preflight222(const struct nes_rom_spi_io *io){
 uint32_t started=getticks();
 nes_startup222=(struct nes_startup222){0};
 nes_boot214=(struct nes_boot214){0};nes_plan215=(struct nes_plan215){0};
 nes_startup222.signals=boot214_signals();
 nes_startup222.reason=startup_probe222(io,nes_startup222.reply,true);
 nes_startup222.ticks=getticks()-started;
 nes_startup222.signals|=boot214_signals()<<8;
 if(!get_snes_reset()||!nes_cf86_check094())nes_startup222.reason=NES_STARTUP222_GUARD;
 return nes_startup222.reason==NES_STARTUP222_READY||nes_startup222.reason==NES_STARTUP222_NO_RESPONSE;
}
static bool native_postflight222(const struct nes_rom_spi_io *io){
 if(nes_startup222.reason==NES_STARTUP222_READY)return true;
 uint32_t started=getticks();
 nes_startup222.post_reason=startup_probe222(io,nes_startup222.post_reply,false);
 nes_startup222.ticks+=getticks()-started;
 nes_startup222.signals|=boot214_signals()<<16;
 return nes_startup222.post_reason==NES_STARTUP222_READY;
}
