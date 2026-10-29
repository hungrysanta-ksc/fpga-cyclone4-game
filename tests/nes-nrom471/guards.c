// SPDX-License-Identifier: MIT
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "nes_native165.h"
uint32_t nes_cost471_crc_errors,nes_cost471_transfer_stops;
static struct nes_native165 s;
static uint8_t crc8(const uint8_t *p,unsigned n){uint8_t c=0;while(n--){c^=*p++;for(int i=0;i<8;i++)c=(c&128)?(uint8_t)((c<<1)^7):(uint8_t)(c<<1);}return c;}
static bool packet(unsigned k,unsigned index,uint64_t v,unsigned gen){uint8_t b[12];unsigned w=k==6?2:8,t=(k<<13)|index;b[0]=t>>8;b[1]=t;b[2]=gen>>8;b[3]=gen;for(unsigned i=0;i<w;i++)b[4+i]=(uint8_t)(v>>(8*(w-1-i)));return nes_native165_packet(&s,s.token_valid?s.next_token:0,b,w+4);}
static void begin(void){nes_native165_reset(&s);assert(packet(7,0,(UINT64_C(0x2232)<<48)|(UINT64_C(1)<<42)|(UINT64_C(1)<<36)|(UINT64_C(224)<<28),7));}
static void rows(void){begin();assert(packet(6,0x1020,1,7));for(unsigned i=0;i<28;i++)assert(packet(7,0x1907,0,7));}
static bool bad_transfer;
static bool transfer(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){(void)ctx;memset(rx,0,n);if(tx[0]==0xd0){rx[1]=0xd6;rx[2]=1;rx[6]=1;rx[7]=crc8(rx+1,6);return true;}assert(tx[0]==0xd1);return !bad_transfer;}
int main(void){unsigned negatives=0;
 begin();assert(!packet(6,0x1000,1,7)&&s.error==37);negatives++;
 begin();assert(!packet(6,0x1021,1,7)&&s.error==37);negatives++;
 begin();assert(!packet(6,0x1001,0x8000,7)&&s.error==37);negatives++;
 begin();assert(!packet(6,0x1001,1,8)&&s.error==37);negatives++;
 rows();assert(!packet(7,0x1c00,0,7)&&s.error==38);negatives++;
 rows();assert(!packet(7,0x1cff,0,7)&&s.error==38);negatives++;
 rows();assert(!packet(7,0x1c01,UINT64_C(1)<<49,7)&&s.error==38);negatives++;
 rows();assert(!packet(7,0x1c01,0,8)&&s.error==38);negatives++;
 nes_native165_reset(&s);assert(!packet(7,0,(UINT64_C(0x2231)<<48),7)&&s.error==2);negatives++;
 const unsigned v[]={0,0x6000,0x7000,0x73a0,0x73e0,0x7fbf,0x7fff};
 const unsigned expected[]={0x1000,0x7000,0x20,0x800,0,0x41f,0xc1f};
 for(unsigned i=0;i<7;i++){rows();assert(packet(7,0x1cdf,(UINT64_C(0x1e)<<36)|v[i],7));assert((s.raster[0]&32767)==v[i]&&(s.raster[1]&32767)==expected[i]&&s.at[4]==224);}
 nes_native165_reset(&s);bad_transfer=true;assert(!nes_native165_poll(&s,transfer,0)&&s.error==23&&nes_cost471_transfer_stops==1&&!nes_cost471_crc_errors);
 nes_native165_reset(&s);bad_transfer=false;assert(!nes_native165_poll(&s,transfer,0)&&s.error==23&&nes_cost471_transfer_stops==1&&nes_cost471_crc_errors==1);
 printf("PASS471 guards negative=%u raster_wrap=7 transfer_vs_crc=2\n",negatives);return 0;
}
