/* SPDX-License-Identifier: MIT */
/* Native synthetic boundaries; target M4 and real SPI replay are separate. */
#include "nes_native165.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
uint32_t nes_cost471_crc_errors,nes_cost471_transfer_stops;
void base_reset(struct nes_native165 *);
void candidate_reset(struct nes_native165 *);
bool base_packet(struct nes_native165 *,uint16_t,const uint8_t *,unsigned);
bool candidate_packet(struct nes_native165 *,uint16_t,const uint8_t *,unsigned);
uint16_t crc476_base(const uint8_t *,unsigned);
uint16_t crc476_candidate(const uint8_t *,unsigned);
static struct nes_native165 a,b;
static unsigned cases;
static void init(void){
 base_reset(&a);a.generation=1;a.state=NES_NATIVE165_RECEIVING;a.next_kind=5;
 a.counts[0]=a.at[0]=33;a.counts[1]=a.at[1]=224;
 a.counts[4]=a.at[4]=224;a.counts[5]=a.at[5]=32;
}
static void set(unsigned tag,unsigned kind){
 a.required[tag>>2]|=(uint8_t)(kind<<((tag&3)*2));
}
static void check(unsigned missing,bool accept){
 const uint8_t meta[12]={0xe0,4,0,1,0,0,0,0,0,0,0,0};
 a.missing=(uint16_t)missing;b=a;
 bool x=base_packet(&a,0,meta,sizeof(meta)),y=candidate_packet(&b,0,meta,sizeof(meta));
 assert(x==accept&&y==x&&!memcmp(&a,&b,sizeof(a)));
 if(accept){
  unsigned at=0;
  for(unsigned tag=0;tag<8192;tag++){
   unsigned kind=(a.required[tag>>2]>>((tag&3)*2))&3;
   if(!kind)continue;
   assert(at<a.ntiles&&a.tiles[at].tag==tag&&a.tiles[at].kind==kind);at++;
  }
  assert(at==missing&&at==a.ntiles&&a.next_kind==7&&a.missing==0);
 }else assert(a.state==NES_NATIVE165_FAILED&&a.error==34);
 cases++;
}
int main(void){
 uint8_t bytes[256];
 for(unsigned i=0;i<sizeof(bytes);i++)bytes[i]=(uint8_t)(i*37+19);
 for(unsigned n=0;n<=256;n++)assert(crc476_base(bytes,n)==crc476_candidate(bytes,n));
 assert(crc476_candidate((const uint8_t *)"123456789",9)==0x29b1);
 /* All three-byte strings cover every 16-bit intermediate CRC and next byte. */
 for(unsigned value=0;value<0x1000000u;value++){
  uint8_t p[3]={(uint8_t)(value>>16),(uint8_t)(value>>8),(uint8_t)value};
  assert(crc476_base(p,3)==crc476_candidate(p,3));
 }
 init();check(0,true);
 for(unsigned tag=0;tag<8192;tag++)for(unsigned kind=1;kind<=3;kind++){
  init();set(tag,kind);check(1,true);
 }
 init();for(unsigned i=0;i<512;i++)set(i,1+i%3);check(512,true);
 init();for(unsigned i=0;i<512;i++)set(i*16+15,1+i%3);check(512,true);
 uint32_t seed=0x4762026;
 for(unsigned run=0;run<512;run++){
  init();unsigned count=0,want=1+run;
  while(count<want){
   seed^=seed<<13;seed^=seed>>17;seed^=seed<<5;unsigned tag=seed&8191;
   if((a.required[tag>>2]>>((tag&3)*2))&3)continue;
   set(tag,1+(seed>>16)%3);count++;
  }
  check(want,true);
 }
 init();check(513,false);
 init();set(8191,2);check(0,false);
 init();for(unsigned i=0;i<513;i++)set(i,3);check(512,false);
 printf("PASS476 exhaustive_crc3=16777216 bitmap_cases=%u unchanged_state_and_order=1\n",cases);
 return 0;
}
