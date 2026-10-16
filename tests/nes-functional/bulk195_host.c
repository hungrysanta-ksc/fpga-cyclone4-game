/* SPDX-License-Identifier: MIT */
#include "nes_sink_bulk195.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct nes_native_sink165 sink;
static uint8_t sent[256];static unsigned calls,queued,checks;static int fault;
static bool exchange(void *ctx,const uint8_t *b,unsigned n,uint8_t a[12]){
 (void)ctx;calls++;assert(n<=sizeof(sent));memcpy(sent,b,n);
 a[0]=b[0]==3?1:0;a[1]=b[0];memcpy(a+2,b+2,8);a[10]=0x65;a[11]=0x9a;
 if(fault>=0&&fault<12)a[fault]^=1;
 return fault!=12;
}
static bool enqueue(void *ctx,const uint8_t *b,unsigned n){(void)ctx;(void)b;(void)n;queued++;return false;}
static void init(void){fault=-1;calls=queued=0;nes_sink165_reset(&sink,exchange,NULL);sink.enqueue=enqueue;assert(nes_sink165_begin(&sink,123));calls=0;}
static void put16(uint8_t *d,unsigned v){d[0]=(uint8_t)v;d[1]=(uint8_t)(v>>8);}
static void descriptor(uint8_t d[12],unsigned kind,unsigned length,unsigned offset){
 memset(d,0,12);d[0]=1;d[1]=(uint8_t)kind;put16(d+2,length);put16(d+4,offset);put16(d+6,123);
 d[8]=0x78;d[9]=0x56;d[10]=0x34;d[11]=0x12;
}
int main(void){
 uint8_t d[12];
 /* Every legal length, both kinds, including the final section boundary. */
 for(unsigned kind=0;kind<2;kind++)for(unsigned length=kind?32:16;length<=2048;length+=kind?32:16){
  init();unsigned unit=kind?32:16,limit=kind?4096:16384,at=limit-length;
  if(kind)sink.obj_next=(uint16_t)(at/unit);else sink.bg_next=(uint16_t)(at/unit);
  descriptor(d,kind,length,at);assert(nes_sink195_bulk(&sink,d));
  assert(calls==1&&!queued&&sink.sequence==2&&sink.state==NES_SINK165_BUILD&&!sink.displayed);
  const uint8_t head[10]={7,(uint8_t)kind,1,0,1,0,0,0,123,0};assert(!memcmp(sent,head,10));
  assert(!memcmp(sent+10,d+4,2)&&sent[12]==4&&sent[13]==0&&!memcmp(sent+14,d+2,2)&&!memcmp(sent+16,d+8,4));
  assert((kind?sink.obj_next:sink.bg_next)==limit/unit);checks++;
 }
 for(unsigned bad=0;bad<14;bad++){
  init();descriptor(d,0,16,0);
  switch(bad){
   case 0:d[0]=0;break;case 1:d[0]=3;break;case 2:d[1]=2;break;
   case 3:put16(d+2,0);break;case 4:put16(d+2,2064);break;
   case 5:put16(d+2,15);break;case 6:put16(d+4,1);break;
   case 7:put16(d+4,16384);break;case 8:put16(d+4,16);break;
   case 9:put16(d+6,124);break;case 10:memset(d+8,255,4);break;
   case 11:d[1]=1;break;
   case 12:put16(d+4,16368);put16(d+2,32);sink.bg_next=1023;break;
   case 13:break;
  }
  unsigned old=sink.bg_next;assert(!nes_sink195_bulk(&sink,bad==13?NULL:d));
  assert(!calls&&!queued&&sink.bg_next==old&&sink.state==NES_SINK165_FAULT);checks++;
 }
 for(int f=0;f<=12;f++){
  init();descriptor(d,0,16,0);fault=f;assert(!nes_sink195_bulk(&sink,d));
  assert(calls==1&&!queued&&!sink.bg_next&&sink.sequence==1&&sink.state==NES_SINK165_FAULT&&!sink.displayed);
  fault=-1;assert(!nes_sink195_bulk(&sink,d)&&calls==1);checks++;
 }
 init();descriptor(d,0,16,0);sink.sequence=UINT16_MAX;assert(!nes_sink195_bulk(&sink,d)&&!calls&&!sink.bg_next);checks++;
 init();descriptor(d,0,16,0);memset(d+8,0,4);assert(nes_sink195_bulk(&sink,d));checks++;
 for(unsigned state=0;state<4;state++)if(state!=NES_SINK165_BUILD){
  init();sink.state=(uint8_t)state;descriptor(d,0,16,0);assert(!nes_sink195_bulk(&sink,d)&&!calls&&!sink.bg_next);checks++;
 }
 /* Repeated ownership cannot advance the same slot twice. */
 init();descriptor(d,0,16,0);assert(nes_sink195_bulk(&sink,d));assert(!nes_sink195_bulk(&sink,d)&&calls==1&&sink.bg_next==1);checks++;
 printf("PASS BULK195 checks=%u\n",checks);return 0;
}
