// SPDX-License-Identifier: MIT
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "nes_native165.h"
extern bool nes_native165_packet_ref(struct nes_native165 *,uint16_t,const uint8_t *,unsigned);
extern bool nes_native165_prepare_ref(struct nes_native165 *,bool,nes_native165_transfer_fn,void *);
static struct nes_native165 current,reference;
static unsigned calls;
static uint8_t crc8(uint8_t c,uint8_t v){c^=v;for(int i=0;i<8;i++)c=(c&128)?(uint8_t)((c<<1)^7):(uint8_t)(c<<1);return c;}
static bool reply(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 struct nes_native165 *s=ctx;assert(n==8);assert(tx[0]==(calls==1?0xd3:0xd0));
 if(calls==1)assert(tx[4]==1&&(((unsigned)tx[2]<<8)|tx[3])==s->generation);
 memset(rx,0,n);rx[1]=0xd6;rx[2]=2;for(unsigned i=1;i<7;i++)rx[7]=crc8(rx[7],rx[i]);calls++;return true;
}
static unsigned consume(const char *name,struct nes_native165 *s,bool old){
 FILE *f=fopen(name,"r");assert(f);unsigned tok,n,blocks=0;char hex[513];uint8_t bytes[256];
 nes_native165_reset(s);calls=0;
 while(fscanf(f,"%u %u %512s",&tok,&n,hex)==3){
  assert(n&&n<=256&&strlen(hex)==n*2);for(unsigned i=0;i<n;i++){unsigned v;assert(sscanf(hex+2*i,"%2x",&v)==1);bytes[i]=(uint8_t)v;}
  if(s->state==NES_NATIVE165_COMPLETE)assert((old?nes_native165_prepare_ref:nes_native165_prepare)(s,true,reply,s));
  assert((old?nes_native165_packet_ref:nes_native165_packet)(s,(uint16_t)tok,bytes,n));blocks++;
 }
 assert(feof(f));fclose(f);assert(calls==3&&s->state==NES_NATIVE165_COMMITTED);return blocks;
}
int main(int argc,char **argv){
 assert(argc==3);unsigned a=consume(argv[1],&reference,true),b=consume(argv[2],&current,false);
 assert(current.records==reference.records&&current.generation==reference.generation&&current.bytes==reference.bytes);
 assert(!memcmp(current.counts,reference.counts,sizeof current.counts));
 assert(!memcmp(current.at,reference.at,sizeof current.at));
 assert(!memcmp(current.maps,reference.maps,sizeof current.maps));
 assert(!memcmp(current.rows,reference.rows,sizeof current.rows));
 assert(!memcmp(current.objects,reference.objects,sizeof current.objects));
 assert(!memcmp(current.exceptions,reference.exceptions,sizeof current.exceptions));
 assert(!memcmp(current.raster,reference.raster,sizeof current.raster));
 assert(!memcmp(current.palette,reference.palette,sizeof current.palette));
 assert(!memcmp(current.raw_pixels,reference.raw_pixels,sizeof current.raw_pixels));
 assert(current.ntiles==reference.ntiles&&!memcmp(current.tiles,reference.tiles,current.ntiles*sizeof current.tiles[0]));
 printf("PASS471 canonical generation=%u records=%u old_blocks=%u new_blocks=%u\n",current.generation,current.records,a,b);
 return 0;
}
