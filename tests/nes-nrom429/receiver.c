// SPDX-License-Identifier: MIT
// Replay actual CRC-checked RTL blocks through the unmodified 227 receiver.
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "nes_native165.h"
static struct nes_native165 receiver;
static unsigned calls;
static uint8_t crc8(uint8_t c,uint8_t v){c^=v;for(int i=0;i<8;i++)c=(c&0x80)?(uint8_t)((c<<1)^7):(uint8_t)(c<<1);return c;}
static bool reply(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 (void)ctx;assert(n==8);assert(tx[0]==(calls==1?0xd3:0xd0));if(calls==1)assert(tx[4]==1 && (((unsigned)tx[2]<<8)|tx[3])==receiver.generation);
 memset(rx,0,n);rx[1]=0xd6;rx[2]=2;uint8_t c=0;for(int i=1;i<7;i++)c=crc8(c,rx[i]);rx[7]=c;calls++;return true;
}
int main(int argc,char **argv){
 assert(argc==2);FILE *f=fopen(argv[1],"r");assert(f);nes_native165_reset(&receiver);
 unsigned token,n,blocks=0,prepared=0;char hex[513];uint8_t bytes[256];
 while(fscanf(f,"%u %u %512s",&token,&n,hex)==3){
  assert(n>0 && n<=256 && strlen(hex)==n*2);for(unsigned i=0;i<n;i++){unsigned v;assert(sscanf(hex+2*i,"%2x",&v)==1);bytes[i]=(uint8_t)v;}
  if(receiver.state==NES_NATIVE165_COMPLETE){assert(!prepared);assert(nes_native165_prepare(&receiver,true,reply,NULL));assert(calls==3);prepared=1;}
  assert(nes_native165_packet(&receiver,(uint16_t)token,bytes,n));blocks++;
 }
 assert(feof(f));fclose(f);assert(prepared && receiver.state==NES_NATIVE165_COMMITTED && blocks>=2);
 printf("PASS 227 receiver committed generation=%u records=%u blocks=%u prepare_calls=%u\n",receiver.generation,receiver.records,blocks,calls);return 0;
}
