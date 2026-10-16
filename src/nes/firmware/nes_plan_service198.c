/* SPDX-License-Identifier: MIT */
#include "nes_plan_service198.h"
#include "nes_plan_wire196.h"
#include <string.h>
static uint8_t crc8(const uint8_t *b,unsigned n){uint8_t c=0;while(n--){c^=*b++;for(unsigned i=0;i<8;i++)c=(uint8_t)(c&128?(c<<1)^7:c<<1);}return c;}
static uint16_t crc16(const uint8_t *b,unsigned n){uint16_t c=65535;while(n--){c^=(uint16_t)*b++<<8;for(unsigned i=0;i<8;i++)c=(uint16_t)(c&32768?(c<<1)^0x1021:c<<1);}return c;}
static bool fail(struct nes_plan198 *p,uint8_t e){if(!p->error)p->error=e;return false;}
static bool valid(struct nes_plan198 *p){
 if(p->error)return false;
 if(!p->transfer||!p->guard||!p->sink||!p->poll_limit||p->finished||p->sink->state!=NES_SINK165_BUILD||
    (p->started&&p->generation!=p->sink->generation))return fail(p,1);
 if(!p->guard(p->ctx))return fail(p,2);
 return true;
}
static bool poll(struct nes_plan198 *p,uint8_t *flags){
 uint8_t tx[20]={0xe8},rx[20];if(!valid(p))return false;
 if(!p->transfer(p->ctx,tx,rx,20))return fail(p,3);
 if(rx[1]!=0xd7||rx[2]!=2||rx[18]||crc8(rx+1,18)!=rx[19]||(rx[3]&0xfc)||
    (unsigned)rx[4]*256+rx[5]!=p->sent||rx[6]>1)return fail(p,4);
 if(rx[6]){
  if(!p->guard(p->ctx)||!nes_sink195_bulk(p->sink,rx+6))return fail(p,5);
  *flags=0;
 }else{
  for(unsigned i=7;i<18;i++)if(rx[i])return fail(p,4);
  *flags=rx[3];
 }
 return true;
}
static bool flush(struct nes_plan198 *p){
 if(!p->count)return true;
 if(p->sent==65535)return fail(p,1);
 uint8_t flags;unsigned n=p->bytes;uint8_t *b=p->buffer;
 b[0]=0xe9;b[1]=(uint8_t)n;b[2]=(uint8_t)(n>>8);b[3]=p->count;
 uint16_t c=crc16(b+4,n);b[n+4]=(uint8_t)(c>>8);b[n+5]=(uint8_t)c;b[n+6]=crc8(b,n+6);b[n+7]=0xa5;
 for(unsigned i=0;i<p->poll_limit;i++){
  if(!poll(p,&flags))return false;
  if(flags&2)return fail(p,4);
  if(flags&1){
   if(!p->guard(p->ctx))return fail(p,2);
   // Only one248B buffer, no second receive copy on ARM stack.
   if(!p->transfer(p->ctx,b,b,n+8))return fail(p,3);
   p->sent++;p->bytes=0;p->count=0;return true;
  }
 }
 return fail(p,6);
}
static bool append(struct nes_plan198 *p,const struct nes_plan191 *q){
 uint8_t encoded[32];uint16_t ignored;unsigned n=nes_plan196_encode(q,encoded,&ignored);
 if(!n)return fail(p,1);
 if(p->count==15||p->bytes+n>240)if(!flush(p))return false;
 memcpy(p->buffer+4+p->bytes,encoded,n);p->bytes+=(uint16_t)n;p->count++;
 return p->count<15||flush(p);
}
bool nes_plan198_emit(void *ctx,const struct nes_plan191 *q){
 struct nes_plan198 *p=ctx;if(!p||!q)return false;
 if(!valid(p))return false;
 if(q->kind>2||q->generation!=p->sink->generation)return fail(p,1);
 p->started=true;p->generation=q->generation;return append(p,q);
}
bool nes_plan198_finish(struct nes_plan198 *p){
 if(!p)return false;
 if(!valid(p))return false;
 if(!p->started)return fail(p,1);
 struct nes_plan191 end={0};end.kind=3;end.generation=p->generation;
 for(unsigned i=0;i<8;i++)end.alt[i]=UINT16_MAX;
 if(!append(p,&end)||!flush(p))return false;
 uint8_t flags;
 for(unsigned i=0;i<p->poll_limit;i++){
  if(!poll(p,&flags))return false;
  if(flags&2){p->finished=true;return true;}
 }
 return fail(p,6);
}
