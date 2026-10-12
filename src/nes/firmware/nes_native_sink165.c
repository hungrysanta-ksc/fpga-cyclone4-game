/* SPDX-License-Identifier: MIT */
#include "nes_native_sink165.h"
#include <string.h>
static void put16(uint8_t *b,unsigned v){b[0]=(uint8_t)v;b[1]=(uint8_t)(v>>8);}
static bool fail(struct nes_native_sink165 *s,unsigned e){s->error=(uint8_t)e;s->state=NES_SINK165_FAULT;return false;}
void nes_sink165_reset(struct nes_native_sink165 *s,nes_sink165_exchange_fn fn,void *ctx){
 memset(s,0,sizeof(*s));s->exchange=fn;s->ctx=ctx;
}
static bool packet(struct nes_native_sink165 *s,unsigned op,unsigned section,unsigned at,const uint8_t *data,unsigned n){
 uint8_t b[256]={0},ack[12]={0};uint8_t old=s->state;
 if(!s->exchange||n>240||s->sequence==UINT16_MAX||s->state==NES_SINK165_BUSY||s->state==NES_SINK165_FAULT)return fail(s,1);
 b[0]=(uint8_t)op;b[1]=(uint8_t)section;put16(b+2,s->sequence);
 for(unsigned i=0;i<4;i++)b[4+i]=(uint8_t)(s->serial>>(i*8));
 put16(b+8,s->generation);put16(b+10,at);put16(b+12,n);if(n)memcpy(b+16,data,n);
 s->state=NES_SINK165_BUSY; /* arm before publishing; never retry ambiguity */
 if(!s->exchange(s->ctx,b,n+16,ack))return fail(s,2);
 if(ack[0]!=(op==3?1:0)||ack[1]!=op||memcmp(ack+2,b+2,8)||ack[10]!=0x65||ack[11]!=0x9a)return fail(s,3);
 s->sequence++;s->state=old;return true;
}
bool nes_sink165_begin(struct nes_native_sink165 *s,uint16_t generation){
 if(s->state!=NES_SINK165_IDLE||s->serial==UINT32_MAX)return false;
 s->serial++;s->generation=generation;s->sequence=0;s->bg_next=s->obj_next=0;
 if(!packet(s,1,0,0,NULL,0))return false;
 s->state=NES_SINK165_BUILD;return true;
}
bool nes_sink165_pattern(void *ctx,unsigned kind,unsigned slot,const uint8_t *b,unsigned n){
 struct nes_native_sink165 *s=ctx;
 if(s->state!=NES_SINK165_BUILD)return false;
 if(!b||kind>1||slot>=(kind?128u:1024u)||n!=(kind?32u:16u)||slot!=(kind?s->obj_next:s->bg_next))return fail(s,4);
 if(!packet(s,2,kind,slot*n,b,n))return false;
 if(kind)s->obj_next++;else s->bg_next++;
 return true;
}
bool nes_sink165_seal(struct nes_native_sink165 *s,const struct nes_native_video165 *p,uint16_t budget){
 if(s->state!=NES_SINK165_BUILD)return false;
 if(!p||!p->valid||p->generation!=s->generation||p->bg_count!=s->bg_next||!s->bg_next||p->obj_count!=s->obj_next||!p->hdma_size||p->hdma_size>1121)return fail(s,5);
 const uint8_t *data[4]={p->map,p->cgram,p->oam,p->hdma};
 uint16_t size[6]={(uint16_t)(p->bg_count*16),(uint16_t)(p->obj_count*32),4096,512,544,p->hdma_size};
 for(unsigned k=2;k<6;k++)for(unsigned at=0;at<size[k];at+=240){
  unsigned n=size[k]-at;if(n>240)n=240;
  if(!packet(s,2,k,at,data[k-2]+at,n))return false;
 }
 uint8_t descriptor[18];for(unsigned i=0;i<6;i++)put16(descriptor+i*2,size[i]);
 put16(descriptor+12,p->hofs[0]);put16(descriptor+14,p->vofs[0]);put16(descriptor+16,budget);
 if(!packet(s,3,0,0,descriptor,18))return false;
 s->displayed=true;s->state=NES_SINK165_IDLE;return true;
}
