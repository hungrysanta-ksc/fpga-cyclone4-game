/* SPDX-License-Identifier: MIT */
#include "nes_resident211.h"
#include <string.h>
static bool bit(const uint8_t *b,unsigned i){return (b[i/8]>>(i%8))&1;}
static void set(uint8_t *b,unsigned i){b[i/8]|=(uint8_t)(1u<<(i%8));}
static void clear(uint8_t *b,unsigned i){b[i/8]&=(uint8_t)~(1u<<(i%8));}
void nes_resident211_reset(struct nes_resident211 *s){
 memset(s,0,sizeof *s);memset(s->bg,255,sizeof s->bg);memset(s->obj,255,sizeof s->obj);
 s->map_stale[0]=s->map_stale[1]=UINT64_MAX;
}
void nes_resident211_abort(struct nes_resident211 *s){
 s->fault=true;s->open=s->prepared=false;s->write=NULL;s->ctx=NULL;
 memset(s->resident,0,sizeof s->resident);
 s->map_stale[0]=s->map_stale[1]=UINT64_MAX;
}
bool nes_resident211_begin(struct nes_resident211 *s,uint32_t epoch,bool immutable,
                          uint16_t generation,nes_resident211_write_fn write,void *ctx){
 if(!s||s->fault)return false;
 if(!immutable||!write||s->open||s->serial==UINT32_MAX){nes_resident211_abort(s);return false;}
 if(s->epoch!=epoch){
  memset(s->bg,255,sizeof s->bg);memset(s->obj,255,sizeof s->obj);
  memset(s->resident,0,sizeof s->resident);s->bg_slots=s->obj_slots=0;s->epoch=epoch;
 }
 s->target=s->displayed?(uint8_t)(1-s->active):0;s->generation=generation;s->serial++;
 s->open=true;s->prepared=false;s->writes=s->hits=0;s->write=write;s->ctx=ctx;
 memset(s->used,0,sizeof s->used);memset(s->dirty,0,sizeof s->dirty);
 return true;
}
static bool ordinary(const struct nes_plan191 *q){
 if(q->kind==2)return true;
 if(q->tag>=8192||q->kind>1||(q->kind==0&&q->mask!=255))return false;
 for(unsigned i=0;i<8;i++)if(q->alt[i]!=UINT16_MAX)return false;
 for(unsigned i=0;i<16;i++)if(q->row[i]!=i/2)return false;
 return true;
}
unsigned nes_resident211_slot(struct nes_resident211 *s,struct nes_native_video165 *v,
                             uint64_t exact,struct nes_plan191 *q){
 if(!s||!v||!q||s->fault||!s->open||s->prepared||q->generation!=s->generation||q->kind>2)return UINT16_MAX;
 unsigned kind=q->kind==1,base=kind?1024:0,limit=kind?128:1024;
 unsigned first=kind||q->kind==2?0:1,stop=q->kind==2?1:limit,slot=stop;
 bool retain=ordinary(q);
 uint32_t key=q->kind==2?65534u:q->tag|(kind?(uint32_t)q->mask<<13:0);
 /* Scratch exact keys only deduplicate THIS frame, including row/alt shapes.
  * Used slots cannot be evicted by later patterns in the same frame. */
 unsigned live=kind?v->obj_count:v->bg_count;
 for(unsigned i=first;i<stop&&i<live;i++)if(bit(s->used,base+i)&&
    (kind?v->obj_keys[i]==(uint32_t)exact:v->bg_keys[i]==exact))return i;
 unsigned occupied=kind?s->obj_slots:s->bg_slots;
 if(retain)for(unsigned i=first;i<stop&&i<occupied;i++)if(!bit(s->used,base+i)&&
    (kind?s->obj[i]==key:s->bg[i]==key)){slot=i;break;}
 if(slot==stop){
  /* Prefer invalid entries; otherwise bounded deterministic eviction. The
   * old visible bank remains untouched even if its metadata key is retired. */
  for(unsigned i=first;i<stop&&i<occupied;i++)if(!bit(s->used,base+i)&&
     (kind?s->obj[i]==UINT32_MAX:s->bg[i]==UINT16_MAX)){slot=i;break;}
  if(slot==stop&&occupied<stop)slot=occupied<first?first:occupied;
  if(slot==stop)for(unsigned i=first;i<stop;i++)if(!bit(s->used,base+i)){slot=i;break;}
 }
 if(slot==stop){nes_resident211_abort(s);return UINT16_MAX;}
 unsigned index=base+slot;
 if(kind){if(s->obj_slots<=slot)s->obj_slots=(uint16_t)(slot+1);}
 else if(s->bg_slots<=slot)s->bg_slots=(uint16_t)(slot+1);
 bool equal=retain&&(kind?s->obj[slot]==key:s->bg[slot]==key);
 if(!equal){
  clear(s->resident[0],index);clear(s->resident[1],index);
  if(kind)s->obj[slot]=retain?key:UINT32_MAX;else s->bg[slot]=retain?(uint16_t)key:UINT16_MAX;
 }
 set(s->used,index);
 if(kind){v->obj_keys[slot]=(uint32_t)exact;if(v->obj_count<=slot)v->obj_count=(uint16_t)(slot+1);}
 else{v->bg_keys[slot]=exact;if(v->bg_count<=slot)v->bg_count=(uint16_t)(slot+1);}
 if(q->kind!=2&&equal&&bit(s->resident[s->target],index)){s->hits++;return slot;}
 q->slot=(uint16_t)slot;
 if(!s->write(s->ctx,s->target,q)){nes_resident211_abort(s);return UINT16_MAX;}
 set(s->dirty,index);s->writes++;return slot;
}
bool nes_resident211_prepare(struct nes_resident211 *s,uint64_t changed_from_display){
 if(!s||s->fault||!s->open||s->prepared)return false;
 /* Current producer comparison is against LAST DISPLAY, not destination.
  * Union propagates skipped intermediate changes to the alternating bank. */
 s->map_stale[0]|=changed_from_display;s->map_stale[1]|=changed_from_display;
 s->map_upload=s->map_stale[s->target];s->prepared=true;return true;
}
bool nes_resident211_commit(struct nes_resident211 *s,uint32_t serial,uint16_t generation,
                           unsigned bank,bool displayed){
 if(!s||s->fault)return false;
 if(!s->open||!s->prepared||!displayed||serial!=s->serial||generation!=s->generation||bank!=s->target){
  nes_resident211_abort(s);return false;
 }
 for(unsigned i=0;i<NES_RESIDENT211_BITS;i++)s->resident[bank][i]|=s->dirty[i];
 s->map_stale[bank]=0;s->active=(uint8_t)bank;s->displayed=true;s->open=s->prepared=false;
 s->write=NULL;s->ctx=NULL;return true;
}
