/* SPDX-License-Identifier: MIT */
#include "nes_sink_spi165.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static FILE *trace;
static unsigned calls,guards,fail_call,fail_guard,corrupt;
static uint8_t packet[256],expected[12];
static uint8_t c8(uint8_t c,uint8_t b){c^=b;for(unsigned i=0;i<8;i++)c=(uint8_t)(c&128?(c<<1)^7:c<<1);return c;}
static bool guard(void *p){(void)p;return ++guards!=fail_guard;}
static bool transfer(void *p,const uint8_t *tx,uint8_t *rx,unsigned n){
 (void)p;unsigned size,b;char t[519],r[519];calls++;
 if(calls==fail_call)return false;
 assert(fscanf(trace,"%u %518s %518s",&size,t,r)==3&&size==n);
 for(unsigned i=0;i<n;i++){assert(sscanf(t+2*i,"%2x",&b)==1&&b==tx[i]);assert(sscanf(r+2*i,"%2x",&b)==1);rx[i]=(uint8_t)b;}
 if(corrupt&&calls==1){
  if(corrupt==1)rx[1]=0xd6;
  if(corrupt==2)rx[2]=0x80;
  if(corrupt==3)rx[2]=1;
  if(corrupt==4)rx[2]=3;
  if(corrupt==5)rx[15]^=1;
  else{rx[15]=0;for(unsigned i=1;i<15;i++)rx[15]=c8(rx[15],rx[i]);}
 }
 return true;
}
static void reset(FILE *f){trace=f;rewind(f);calls=guards=fail_call=fail_guard=corrupt=0;}
int main(int argc,char **argv){
 assert(argc==3);FILE *f=fopen(argv[1],"r"),*vectors=fopen(argv[2],"r");assert(f&&vectors);trace=f;
 struct nes_sink_spi165 s={transfer,NULL,guard,2};uint8_t ack[12];unsigned n,b,packets=0;
 while(fscanf(vectors,"%u",&n)==1){assert(n>=16&&n<=256);for(unsigned i=0;i<n;i++){assert(fscanf(vectors,"%2x",&b)==1);packet[i]=(uint8_t)b;}
  for(unsigned i=0;i<12;i++){assert(fscanf(vectors,"%2x",&b)==1);expected[i]=(uint8_t)b;}
  assert(nes_sink_spi165_exchange(&s,packet,n,ack));assert(memcmp(ack,expected,12)==0);packets++;
 }
 assert(packets==227&&calls==908&&guards==908);unsigned negatives=0;
 rewind(vectors);assert(fscanf(vectors,"%u",&n)==1);for(unsigned i=0;i<n;i++){assert(fscanf(vectors,"%2x",&b)==1);packet[i]=(uint8_t)b;}
 for(unsigned i=1;i<=4;i++){
  reset(f);fail_call=i;assert(!nes_sink_spi165_exchange(&s,packet,n,ack)&&calls==i);negatives++;
  reset(f);fail_guard=i;assert(!nes_sink_spi165_exchange(&s,packet,n,ack)&&calls==i-1);negatives++;
 }
 for(unsigned i=1;i<=5;i++){reset(f);corrupt=i;assert(!nes_sink_spi165_exchange(&s,packet,n,ack)&&calls==1);negatives++;}
 reset(f);s.poll_limit=1;assert(!nes_sink_spi165_exchange(&s,packet,n,ack)&&calls==3);negatives++;
 reset(f);s.poll_limit=0;assert(!nes_sink_spi165_exchange(&s,packet,n,ack)&&calls==0);negatives++;
 reset(f);s.poll_limit=65537;assert(!nes_sink_spi165_exchange(&s,packet,n,ack)&&calls==0);negatives++;
 reset(f);s.poll_limit=2;assert(!nes_sink_spi165_exchange(&s,packet,n-1,ack)&&calls==0);negatives++;
 fclose(f);fclose(vectors);printf("PASS SINKSPI165 packets=%u transactions=908 negatives=%u\n",packets,negatives);return 0;
}
