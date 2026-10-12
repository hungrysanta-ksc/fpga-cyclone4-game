/* SPDX-License-Identifier: MIT */
#include "nes_native_stage165.h"
#include <string.h>
/* Two 32KiB candidates in bank7F. Bank7E client/stack/HDMA remain separate. */
static const uint16_t offset[6]={0,0x4000,0x5000,0x6000,0x6200,0x6500};
static const uint16_t dest[6]={0,0x4000,0x8000,0,0,0};
static const uint8_t kind[6]={0,0,0,1,2,3};
static uint32_t address(unsigned bank,unsigned section,unsigned at){
 return NES_STAGE165_WRAM_BASE+bank*NES_STAGE165_SLOT+offset[section]+at;
}
static bool fail(struct nes_native_stage165 *s,unsigned error){
 s->error=(uint8_t)error;s->state=NES_STAGE165_FAILED;return false;
}
void nes_stage165_reset(struct nes_native_stage165 *s,nes_stage165_read_fn read,nes_stage165_write_fn write,void *ctx){
 memset(s,0,sizeof(*s));s->read=read;s->write=write;s->ctx=ctx;
}
bool nes_stage165_begin(struct nes_native_stage165 *s,uint16_t generation){
 if(s->state!=NES_STAGE165_IDLE||!s->read||!s->write||s->serial==UINT32_MAX)return false;
 s->serial++;s->generation=generation;s->candidate=s->displayed?(uint8_t)(s->current^1):0;
 memset(s->size,0,sizeof(s->size));s->payload=s->charged=0;s->ncommands=s->error=s->section=0;
 s->bg_next=s->obj_next=s->at=s->start=s->end=0;s->run=false;s->state=NES_STAGE165_BUILD;return true;
}
bool nes_stage165_pattern(void *ctx,unsigned k,unsigned slot,const uint8_t *b,unsigned n){
 struct nes_native_stage165 *s=ctx;
 if(s->state!=NES_STAGE165_BUILD)return false;
 if(!b||k>1||slot>=(k?128u:1024u)||n!=(k?32u:16u)||slot!=(k?s->obj_next:s->bg_next))return fail(s,1);
 if(!s->write(s->ctx,address(s->candidate,k,slot*n),b,n))return fail(s,2);
 if(k)s->obj_next++;else s->bg_next++;
 return true;
}
bool nes_stage165_seal(struct nes_native_stage165 *s,const struct nes_native_video165 *p,uint16_t budget){
 if(s->state!=NES_STAGE165_BUILD)return false;
 if(!p||!p->valid||p->generation!=s->generation||p->bg_count!=s->bg_next||!s->bg_next||
    p->obj_count!=s->obj_next||!p->hdma_size||p->hdma_size>1121)return fail(s,3);
 const uint8_t *data[4]={p->map,p->cgram,p->oam,p->hdma};
 s->size[0]=(uint16_t)(p->bg_count*16);s->size[1]=(uint16_t)(p->obj_count*32);
 s->size[2]=4096;s->size[3]=512;s->size[4]=544;s->size[5]=p->hdma_size;
 s->hofs=p->hofs[0];s->vofs=p->vofs[0];s->budget=budget;
 for(unsigned k=2;k<6;k++)for(unsigned at=0;at<s->size[k];at+=64){
  unsigned n=s->size[k]-at;if(n>64)n=64;
  if(!s->write(s->ctx,address(s->candidate,k,at),data[k-2]+at,n))return fail(s,2);
 }
 s->state=NES_STAGE165_DIFF;return true;
}
static bool emit(struct nes_native_stage165 *s,unsigned start,unsigned end){
 if(start==end)return true;
 unsigned n=end-start;
 if(s->ncommands==NES_STAGE165_COMMANDS)return fail(s,4);
 if(s->displayed&&s->charged+n+96>s->budget)return fail(s,5);
 struct nes_stage165_command *c=&s->commands[s->ncommands++];
 c->source=address(s->candidate,s->section,start);c->dest=(uint16_t)(dest[s->section]+start);
 c->size=(uint16_t)n;c->kind=kind[s->section];s->payload+=n;s->charged+=n+96;return true;
}
static void next(struct nes_native_stage165 *s){
 s->section++;s->at=s->start=s->end=0;s->run=false;
 if(s->section==6)s->state=NES_STAGE165_READY;
}
bool nes_stage165_step(struct nes_native_stage165 *s){
 if(s->state!=NES_STAGE165_DIFF)return false;
 unsigned k=s->section,n=s->size[k]-s->at;
 if(!s->displayed||(!s->at&&k>=3&&s->size[k]!=s->old_size[k])){
  if(!emit(s,0,s->size[k]))return false;
  next(s);return true;
 }
 if(!n){if(s->run&&!emit(s,s->start,s->end))return false;next(s);return true;}
 if(n>64)n=64;
 uint8_t a[64],b[64];unsigned old=s->old_size[k]>s->at?s->old_size[k]-s->at:0;
 if(old>n)old=n;
 if(!s->read(s->ctx,address(s->candidate,k,s->at),a,n)||
    (old&&!s->read(s->ctx,address(s->current,k,s->at),b,old)))return fail(s,6);
 if(k>=3){
  if(old!=n||memcmp(a,b,n)){
   if(!emit(s,0,s->size[k]))return false;
   next(s);return true;
  }
 }else for(unsigned i=0;i<n;i+=2){
  unsigned at=s->at+i;
  if(i+2>old||a[i]!=b[i]||a[i+1]!=b[i+1]){
   if(s->run&&at-s->end>32){if(!emit(s,s->start,s->end))return false;s->run=false;}
   if(!s->run){s->start=(uint16_t)at;s->run=true;}
   s->end=(uint16_t)(at+2);
  }
 }
 s->at=(uint16_t)(s->at+n);return true;
}
bool nes_stage165_arm(struct nes_native_stage165 *s){
 if(s->state!=NES_STAGE165_READY)return false;
 s->state=NES_STAGE165_WAIT;return true;
}
bool nes_stage165_ack(struct nes_native_stage165 *s,uint32_t serial,uint16_t generation,bool success){
 if(s->state!=NES_STAGE165_WAIT||serial!=s->serial||generation!=s->generation)return false;
 if(!success){s->error=7;s->state=NES_STAGE165_FAULT;return false;}
 s->current=s->candidate;memcpy(s->old_size,s->size,sizeof(s->size));s->displayed=true;s->state=NES_STAGE165_IDLE;return true;
}
void nes_stage165_abort(struct nes_native_stage165 *s){
 if(s->state==NES_STAGE165_WAIT||s->state==NES_STAGE165_FAULT){s->error=8;s->state=NES_STAGE165_FAULT;}
 else s->state=NES_STAGE165_IDLE;
}
