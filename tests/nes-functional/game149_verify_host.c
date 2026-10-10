/* SPDX-License-Identifier: MIT */
/* Actual materialized MCU verify code, synthetic data and protocol peer.
 * Full384KiB CHECK loop, not a physical RAM test or whole firmware emulation. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "nes_rom_verify.h"
static uint32_t next,source_calls,commands;
static uint8_t flags=2;
static int scenario;
static bool sticky,started;
bool nes_cf86_monitoring094(void){return true;}
bool nes_cf86_fail094(void){sticky=true;return false;}
bool nes_cf86_check094(void){return !sticky;}
static uint8_t value(uint32_t a){return (uint8_t)(a^(a>>8)^(a>>16)^0x5a);}
static bool source(void *ctx,uint32_t a,uint8_t *v){
 (void)ctx;assert(a==source_calls++);*v=value(a);
 return !(scenario==3&&a==0x5ffff);
}
bool nes_game149_transfer(const struct nes_rom_spi_io *io,const uint8_t tx[8],uint8_t rx[8]){
 (void)io;if(sticky)return false;
 uint32_t a=((uint32_t)tx[1]<<16)|((uint32_t)tx[2]<<8)|tx[3];
 uint8_t canonical[8];nes_rom_spi_frame(canonical,tx[0],a,tx[4]);assert(!memcmp(tx,canonical,8));
 commands++;memset(rx,0,8);rx[1]=scenario==1?0x5e:0x5f;
 uint32_t count=0x60000;
 switch(tx[0]){
 case 0x65:rx[2]=flags;break;
 case 0x66:assert(flags==2&&a==0);flags=0x22;break;
 case 0x67:assert(flags==0x22&&a==next);flags=0x62;break;
 case 0x6a:assert(flags==0x62);rx[2]=flags;count=next;rx[3]=value(next);
  if(scenario==2&&next==0x5ffff)rx[3]^=1;
  break;
 case 0x68:assert(flags==0x62&&a==next&&tx[4]==value(next));next++;flags=0x22;break;
 case 0x69:assert(flags==0x22&&a==0x60000&&next==a&&source_calls==a);flags=0x82;break;
 case 0x63:assert(flags==0x82&&a==0x60000);flags=0x86;started=true;break;
 default:assert(0);
 }
 rx[4]=count>>16;rx[5]=count>>8;rx[6]=count;return true;
}
int main(void){
 struct nes_rom_spi_io io={0};struct nes_verify_report r;
 assert(!nes_rom_verify(&io,0x14000,source,0,&r)&&r.error==NES_VERIFY_ARGUMENT);
 assert(!nes_rom_verify(&io,0x18000,source,0,&r)&&r.error==NES_VERIFY_ARGUMENT);
 assert(!nes_rom_verified_start(&io,0x14000));
 assert(nes_rom_verify(&io,0x60000,source,0,&r)&&r.compared==0x60000);
 assert(nes_rom_verified_start(&io,0x60000)&&started);
 unsigned full=commands;
 for(scenario=1;scenario<=3;scenario++){
  next=source_calls=commands=0;flags=2;sticky=started=false;
  assert(!nes_rom_verify(&io,0x60000,source,0,&r));
  assert(r.error==(scenario==1?NES_VERIFY_PROTOCOL:scenario==2?NES_VERIFY_DATA:NES_VERIFY_SOURCE));
  assert(!nes_rom_verified_start(&io,0x60000)&&!started);
  if(scenario>1)assert(r.compared==0x5ffff&&sticky);
 }
 printf("PASS149 verify payload=393216 successful_commands=%u old_sizes=2 old_id=1 last_byte_faults=2\n",full);
 return 0;
}
