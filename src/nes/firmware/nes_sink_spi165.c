/* SPDX-License-Identifier: MIT */
#include "nes_sink_spi165.h"
#include <string.h>
static uint16_t crc16(uint16_t c,uint8_t b){
 c^=(uint16_t)b<<8;for(unsigned i=0;i<8;i++)c=(uint16_t)(c&0x8000?(c<<1)^0x1021:c<<1);return c;
}
static uint8_t crc8(uint8_t c,uint8_t b){
 c^=b;for(unsigned i=0;i<8;i++)c=(uint8_t)(c&0x80?(c<<1)^7:c<<1);return c;
}
static bool status(const uint8_t *b){
 uint8_t c=0;for(unsigned i=1;i<15;i++)c=crc8(c,b[i]);
 return b[1]==0xf6&&b[15]==c&&!(b[2]&0xfc)&&b[2]!=3;
}
bool nes_sink_spi165_exchange(void *ctx,const uint8_t *packet,unsigned n,uint8_t ack[12]){
 struct nes_sink_spi165 *s=ctx;uint8_t tx[259]={0},rx[259];
 if(!s||!s->transfer||!s->guard||!s->poll_limit||s->poll_limit>65536||!packet||!ack||n<16||n>256||n!=16u+packet[12]+((unsigned)packet[13]<<8))return false;
 /* Strict endpoint identity before any packet write; legacy D6/E5 not allowed. */
 tx[0]=0xe0;
 if(!s->guard(s->ctx)||!s->transfer(s->ctx,tx,rx,16)||!status(rx)||(rx[2]&1))return false;
 tx[0]=0xe1;memcpy(tx+1,packet,n);uint16_t c=0xffff;
 for(unsigned i=0;i<=n;i++)c=crc16(c,tx[i]);
 tx[n+1]=(uint8_t)(c>>8);tx[n+2]=(uint8_t)c;
 if(!s->guard(s->ctx)||!s->transfer(s->ctx,tx,rx,n+3))return false;
 memset(tx,0,16);tx[0]=0xe0;
 for(unsigned i=0;i<s->poll_limit;i++){
  if(!s->guard(s->ctx)||!s->transfer(s->ctx,tx,rx,16)||!status(rx))return false;
  if(rx[2]&2){memcpy(ack,rx+3,12);return true;}
 }
 return false; /* ambiguous outcome: caller FAULT until common reset */
}
