/* SPDX-License-Identifier: MIT */
#include "nes_plan_service197.h"
#include "nes_plan_wire196.h"
#include <string.h>
static uint8_t crc8(uint8_t c,const uint8_t *b,unsigned n){
 while(n--){c^=*b++;for(unsigned j=0;j<8;j++)c=(uint8_t)(c&128?(c<<1)^7:c<<1);}return c;
}
static bool fail(struct nes_plan197 *p,uint8_t e){if(!p->error)p->error=e;return false;}
/* Polls always drain ready chunks BEFORE considering plan credit. SNES195
 * validates descriptor and ACK, advances staging only, never display state. */
static bool poll(struct nes_plan197 *p,uint8_t *flags){
 uint8_t tx[20]={0xe8},rx[20];
 if(p->error||!p->transfer||!p->guard||!p->sink||!p->poll_limit)return fail(p,1);
 if(!p->guard(p->ctx))return fail(p,2);
 if(!p->transfer(p->ctx,tx,rx,sizeof(tx)))return fail(p,3);
 if(rx[1]!=0xd7||rx[2]!=1||rx[18]||crc8(0,rx+1,18)!=rx[19]||
    (rx[3]&0xfc)||((unsigned)rx[4]*256+rx[5])!=p->sent||rx[6]>1)return fail(p,4);
 if(p->sink->state!=NES_SINK165_BUILD)return fail(p,5);
 if(rx[6]){
  if(!p->guard(p->ctx)||!nes_sink195_bulk(p->sink,rx+6))return fail(p,5);
  *flags=0; // Re-read after consume: status was a pre-consume snapshot.
 }else{
  for(unsigned i=7;i<18;i++)if(rx[i])return fail(p,4);
  *flags=rx[3];
 }
 return true;
}
bool nes_plan197_emit(void *ctx,const struct nes_plan191 *q){
 struct nes_plan197 *p=ctx;uint8_t tx[38],rx[38],flags;uint16_t crc;
 if(!p||!q)return false;
 if(p->error||p->finished||q->kind>2||!p->sink||q->generation!=p->sink->generation||p->sent==65535)return fail(p,1);
 unsigned n=nes_plan196_encode(q,tx+2,&crc);if(!n)return fail(p,1);
 tx[0]=0xe9;tx[1]=(uint8_t)n;tx[n+2]=(uint8_t)(crc>>8);tx[n+3]=(uint8_t)crc;
 tx[n+4]=crc8(0,tx,n+4);tx[n+5]=0xa5;
 for(unsigned i=0;i<p->poll_limit;i++){
  if(!poll(p,&flags))return false;
  if(flags&2)return fail(p,4);
  if(flags&1){
   if(!p->guard(p->ctx))return fail(p,2);
   if(!p->transfer(p->ctx,tx,rx,n+6))return fail(p,3);
   p->sent++;return true; // Later status checks CRC/decoder/accepted count.
  }
 }
 return fail(p,6);
}
bool nes_plan197_finish(struct nes_plan197 *p){
 if(!p||!p->sink)return false;
 if(p->error||p->finished||!p->sent||p->sent==65535)return fail(p,1);
 struct nes_plan191 end={0};end.kind=3;end.generation=p->sink->generation;
 for(unsigned i=0;i<8;i++)end.alt[i]=UINT16_MAX;
 uint8_t tx[38],rx[38],flags;uint16_t crc;unsigned n=nes_plan196_encode(&end,tx+2,&crc);
 tx[0]=0xe9;tx[1]=(uint8_t)n;tx[n+2]=(uint8_t)(crc>>8);tx[n+3]=(uint8_t)crc;tx[n+4]=crc8(0,tx,n+4);tx[n+5]=0xa5;
 bool submitted=false;
 for(unsigned i=0;i<p->poll_limit;i++){
  if(!poll(p,&flags))return false;
  if(submitted&&(flags&2)){p->finished=true;return true;}
  if(!submitted&&(flags&2))return fail(p,4);
  if(!submitted&&(flags&1)){
   if(!p->guard(p->ctx))return fail(p,2);
   if(!p->transfer(p->ctx,tx,rx,n+6))return fail(p,3);
   p->sent++;submitted=true;
  }
 }
 return fail(p,6); // END+all chunks retired, not SEAL/final display ACK.
}
