// SPDX-License-Identifier: MIT
// Production227 nes_rom_verify.c with a synthetic SPI peer. The peer's RAM is
// populated independently from the NROM layout callback. No hardware IO.
#include "nes_rom_verify.h"
#include "nes_nrom406.h"
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static uint8_t memory[0x60000];
static struct nes_nrom406_profile profile;
static uint32_t next, calls;
static uint8_t flags;
static bool sticky, started;
static int fail_source;
bool nes_cf86_monitoring094(void){return true;}
bool nes_cf86_fail094(void){sticky=true;return false;}
bool nes_cf86_check094(void){return !sticky;}
static uint8_t file_byte(uint32_t offset){return (uint8_t)(offset^(offset>>8)^(offset>>16)^0xa5);}
static bool source(void *ctx,uint32_t at,uint8_t *out){
 (void)ctx; bool from;uint32_t offset;assert(at==calls++);
 if(fail_source && at==0x40000u)return false;
 if(!nes_nrom406_layout(&profile,at,&from,&offset))return false;
 *out=from?file_byte(offset):0;return true;
}
bool nes_game149_transfer(const struct nes_rom_spi_io *io,const uint8_t tx[8],uint8_t rx[8]){
 (void)io;if(sticky)return false;
 uint32_t a=((uint32_t)tx[1]<<16)|((uint32_t)tx[2]<<8)|tx[3];
 uint8_t check[8];nes_rom_spi_frame(check,tx[0],a,tx[4]);assert(!memcmp(check,tx,8));
 memset(rx,0,8);rx[1]=0x74;uint32_t count=0x60000;
 switch(tx[0]){
 case 0x65:rx[2]=flags;break;
 case 0x66:assert(flags==2&&a==0);flags=0x22;break;
 case 0x67:assert(flags==0x22&&a==next);flags=0x62;break;
 case 0x6a:assert(flags==0x62);rx[2]=flags;count=next;rx[3]=memory[next];break;
 case 0x68:assert(flags==0x62&&a==next&&tx[4]==memory[next]);next++;flags=0x22;break;
 case 0x69:assert(flags==0x22&&a==0x60000&&next==a&&calls==a);flags=0x82;break;
 case 0x63:assert(flags==0x82&&a==0x60000);flags=0x86;started=true;break;
 default:assert(0);
 }
 rx[4]=count>>16;rx[5]=count>>8;rx[6]=count;return true;
}
static void fresh(unsigned prg){
 uint8_t h[16]={'N','E','S',0x1a,(uint8_t)prg,1,0,0};
 assert(nes_nrom406_header(h,16u+prg*16384u+8192u,&profile));
 memset(memory,0,sizeof(memory));
 for(uint32_t i=0;i<prg*16384u;i++)memory[i]=file_byte(16u+i);
 for(uint32_t i=0;i<8192u;i++)memory[0x40000u+i]=file_byte(16u+prg*16384u+i);
 next=calls=0;flags=2;sticky=started=false;fail_source=0;
}
int main(void){
 struct nes_rom_spi_io io={0};struct nes_verify_report r;
 for(unsigned prg=1;prg<=2;prg++){
  fresh(prg);assert(nes_rom_verify(&io,0x60000,source,0,&r)&&r.compared==0x60000);
  assert(nes_rom_verified_start(&io,0x60000)&&started);
  const uint32_t faults[]={0,0x8000,0x40000,0x5ffff};
  for(unsigned i=0;i<4;i++){
   fresh(prg);memory[faults[i]]^=1;
   assert(!nes_rom_verify(&io,0x60000,source,0,&r));
   assert(r.error==NES_VERIFY_DATA && r.compared==faults[i] && sticky && !r.stop_ok);
   assert(!nes_rom_verified_start(&io,0x60000)&&!started);
  }
  fresh(prg);fail_source=1;
  assert(!nes_rom_verify(&io,0x60000,source,0,&r));
  assert(r.error==NES_VERIFY_SOURCE && r.compared==0x40000 && sticky && !r.stop_ok);
 }
 puts("NROM406 VERIFY PASS production227 verify source+synthetic peer PRG16/32 faults=10 sticky blocks START");
 return 0;
}
