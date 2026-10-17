/* SPDX-License-Identifier: MIT */
#include "nes_resident211.h"
#include "reference203.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct nes_reference203 r;
static struct nes_native165 input;
static struct nes_native_video165 ref,candidate;
static struct nes_resident211 cache;
static uint16_t lut[64];
static uint8_t refbg[16384],refobj[4096];
static unsigned sizes[2],calls,fail_at,checked,frames;
static unsigned newbytes,referencebytes,mapbytes,reference_mapbytes;
static struct {uint8_t bg[16384],obj[4096],map[4096];} banks[2];
static bool stage(void *ctx,unsigned kind,unsigned slot,const uint8_t *bytes,unsigned n){
 (void)ctx;assert(kind<2&&slot*(kind?32u:16u)==sizes[kind]);
 memcpy((kind?refobj:refbg)+sizes[kind],bytes,n);sizes[kind]+=n;return true;
}
bool reference203_build(const struct nes_reference203 *,const uint16_t [64],
                        struct nes_native_video165 *,bool,nes_native_video165_stage_fn,void *);
#include "scene203.inc"
static void source(unsigned variant,unsigned generation){
 scene(variant);r.generation=(uint16_t)generation;
 /* Same physical CHR bytes across geometry/scroll scenes. The original203
  * fixture varied content per scene, which needs an epoch bump instead. */
 for(unsigned t=0;t<r.ntiles;t++)for(unsigned b=0;b<16;b++)r.tiles[t].data[b]=(uint8_t)(t*31+b*13);
}
static void convert_input(void){
 memset(&input,0,sizeof input);
 memcpy(input.maps,r.maps,sizeof input.maps);memcpy(input.rows,r.rows,sizeof input.rows);
 memcpy(input.palette,r.palette,sizeof input.palette);memcpy(input.objects,r.objects,sizeof input.objects);
 memcpy(input.raster,r.raster,sizeof input.raster);memcpy(input.exceptions,r.exceptions,sizeof input.exceptions);
 memcpy(input.raw_pixels,r.raw_pixels,sizeof input.raw_pixels);memcpy(input.counts,r.counts,sizeof input.counts);
 input.generation=r.generation;input.state=r.state;input.ntiles=r.ntiles;input.patch_count=r.patch_count;
 for(unsigned t=0;t<r.ntiles;t++){input.tiles[t].tag=r.tiles[t].tag;input.tiles[t].kind=r.tiles[t].kind;}
}
static const uint8_t *bytes(unsigned tag){
 for(unsigned t=0;t<r.ntiles;t++)if(r.tiles[t].tag==tag)return r.tiles[t].data;
 assert(0);return NULL;
}
static bool write_slot(void *ctx,unsigned bank,const struct nes_plan191 *q){
 (void)ctx;assert(bank==cache.target&&(!cache.displayed||bank!=cache.active));
 assert(q->generation==cache.generation&&q->kind<=2);calls++;
 if(fail_at&&calls==fail_at)return false;
 unsigned kind=q->kind==1,unit=kind?32:16;assert(q->slot<(kind?128:1024));
 uint8_t *out=(kind?banks[bank].obj:banks[bank].bg)+q->slot*unit;memset(out,0,unit);
 if(q->kind!=2)for(unsigned y=0;y<8;y++)if(q->mask&(1u<<y)){
  const uint8_t *low=bytes(q->alt[y]==UINT16_MAX?q->tag:q->alt[y]);
  out[y*2]=low[q->row[y*2]];out[y*2+1]=bytes(q->tag)[8+q->row[y*2+1]];
 }
 newbytes+=unit;return true;
}
static unsigned word(const uint8_t *p){return p[0]+256u*p[1];}
static unsigned checksum(const void *ptr,unsigned n){
 const uint8_t *b=ptr;unsigned h=2166136261u;for(unsigned i=0;i<n;i++)h=(h^b[i])*16777619u;return h;
}
static void verify_bank(void){
 unsigned bank=cache.target;
 for(unsigned g=0;g<64;g++)if((cache.map_upload>>g)&1){
  memcpy(banks[bank].map+g*64,candidate.map+g*64,64);mapbytes+=64;
 }
 assert(!memcmp(banks[bank].map,candidate.map,4096));
 /* All referenced planar bytes + palette/scroll/OAM/raw controls equal the
  * unchanged actual186 reference converter. Physical slot numbers may differ.
  * This is not a run of the actual65816 consumer or a live NES CPU. */
 for(unsigned i=0;i<2048;i++){
  unsigned a=word(ref.map+i*2),b=word(banks[bank].map+i*2);
  assert((a&0xfc00)==(b&0xfc00));
  assert(!memcmp(refbg+(a&1023)*16,banks[bank].bg+(b&1023)*16,16));checked+=16;
 }
 for(unsigned i=0;i<ref.objects;i++){
  const uint8_t *a=ref.oam+i*4,*b=candidate.oam+i*4;
  assert(a[0]==b[0]&&a[1]==b[1]&&a[3]==b[3]);
  assert(!memcmp(refobj+a[2]*32,banks[bank].obj+b[2]*32,32));checked+=32;
 }
 assert(ref.objects==candidate.objects&&ref.display_mask==candidate.display_mask);
 assert(!memcmp(ref.oam+512,candidate.oam+512,32));
 assert(!memcmp(ref.cgram,candidate.cgram,512));
 assert(ref.hdma_size==candidate.hdma_size&&!memcmp(ref.hdma,candidate.hdma,ref.hdma_size));
 assert(!memcmp(ref.hofs,candidate.hofs,sizeof ref.hofs)&&!memcmp(ref.vofs,candidate.vofs,sizeof ref.vofs));
 assert(ref.patch_count==candidate.patch_count);
 if(ref.patch_count)assert(!memcmp(&ref.patch,&candidate.patch,sizeof ref.patch));
}
static void run_frame(uint32_t epoch){
 convert_input();memset(sizes,0,sizeof sizes);
 assert(reference203_build(&r,lut,&ref,false,stage,NULL));
 unsigned before=checksum(&banks[cache.active],sizeof banks[0]);bool had=cache.displayed;
 assert(nes_resident211_begin(&cache,epoch,true,r.generation,write_slot,NULL));
 assert(nes_native_video211_plan(&input,lut,&candidate,&cache));
 if(had)assert(before==checksum(&banks[cache.active],sizeof banks[0]));
 assert(cache.prepared);verify_bank();
 if(had)assert(before==checksum(&banks[cache.active],sizeof banks[0]));
 assert(nes_resident211_commit(&cache,cache.serial,r.generation,cache.target,true));
 assert(!cache.write&&!cache.ctx&&!cache.open&&!cache.prepared);
 referencebytes+=sizes[0]+sizes[1];reference_mapbytes+=4096;frames++;
}
static void reset(void){
 nes_resident211_reset(&cache);memset(&candidate,0,sizeof candidate);
 memset(banks,0xa5,sizeof banks);calls=fail_at=0;
}
static void compatibility(void){
 reset();for(unsigned pass=0;pass<3;pass++)for(unsigned v=0;v<8;v++){
  source(v,(65530+pass*8+v)&65535);run_frame(1);
 }
 /* Three identical frames warm both physical destinations; third emits only
  * the16B zero-slot anchor, no ordinary pattern or map upload. */
 reset();for(unsigned i=0;i<3;i++){source(0,(65535+i)&65535);run_frame(1);}
 assert(cache.writes==1&&cache.hits>0&&cache.map_upload==0);
 /* Same physical addresses with new contents must miss both banks. */
 source(0,2);for(unsigned t=0;t<r.ntiles;t++)for(unsigned j=0;j<16;j++)r.tiles[t].data[j]^=0x5a;
 run_frame(2);assert(cache.writes>0&&cache.hits==0);
}
static void scrolling(void){
 reset();unsigned start_new=newbytes,start_old=referencebytes,start_map=mapbytes;
 for(unsigned f=0;f<96;f++){
  source(2,100+f);r.ntiles=128;
  for(unsigned t=0;t<r.ntiles;t++){
   r.tiles[t].tag=(uint16_t)t;r.tiles[t].kind=3;
   for(unsigned j=0;j<16;j++)r.tiles[t].data[j]=(uint8_t)(t*31+j*13);
  }
  r.counts[0]=28*33;r.counts[3]=0;
  for(unsigned y=0;y<224;y++){
   r.rows[y]=(uint8_t)(((y/8)<<3)|(y&7));
   r.raster[y]=(UINT64_C(0x1e)<<36)|((uint64_t)(f&7)<<30);
  }
  for(unsigned y=0;y<28;y++)for(unsigned x=0;x<33;x++)
   r.maps[y*33+x]=(uint16_t)(((y*3+x+f/8)%128)|(((x+f/8)%4)<<13));
  run_frame(3);
 }
 assert(newbytes-start_new<referencebytes-start_old);
 printf("SCROLL synthetic_frames=96 pattern_old=%u pattern_new=%u map_new=%u not_physical_fps=1\n",
        referencebytes-start_old,newbytes-start_new,mapbytes-start_map);
}
static bool empty_writer(void *ctx,unsigned bank,const struct nes_plan191 *q){
 (void)ctx;(void)bank;(void)q;return true;
}
static void faults(void){
 unsigned cases=0;
 for(unsigned which=0;which<4;which++){
  reset();source(0,1);run_frame(1);source(2,2);convert_input();
  unsigned bank=cache.active,h=checksum(&banks[bank],sizeof banks[0]);
  assert(nes_resident211_begin(&cache,1,true,2,write_slot,NULL));
  assert(nes_native_video211_plan(&input,lut,&candidate,&cache));
  assert(!nes_resident211_commit(&cache,cache.serial+(which==0),2+(which==1),
                                which==2?cache.active:cache.target,which!=3));
  assert(cache.fault&&!cache.open&&cache.active==bank&&h==checksum(&banks[bank],sizeof banks[0]));
  assert(!nes_resident211_begin(&cache,1,true,3,write_slot,NULL));cases++;
 }
 reset();source(0,1);run_frame(1);source(2,2);convert_input();fail_at=calls+3;
 unsigned active=cache.active,h=checksum(&banks[active],sizeof banks[0]);
 assert(nes_resident211_begin(&cache,1,true,2,write_slot,NULL));
 assert(!nes_native_video211_plan(&input,lut,&candidate,&cache));
 assert(cache.fault&&!candidate.valid&&h==checksum(&banks[active],sizeof banks[0]));cases++;
 reset();assert(!nes_resident211_begin(&cache,1,false,1,write_slot,NULL)&&cache.fault);cases++;
 reset();cache.serial=UINT32_MAX;assert(!nes_resident211_begin(&cache,1,true,1,write_slot,NULL)&&cache.fault);cases++;
 reset();assert(nes_resident211_begin(&cache,1,true,1,empty_writer,NULL));
 assert(!nes_resident211_commit(&cache,cache.serial,1,cache.target,true)&&cache.fault);cases++;
 reset();assert(nes_resident211_begin(&cache,1,true,1,empty_writer,NULL));
 assert(!nes_resident211_begin(&cache,1,true,1,empty_writer,NULL)&&cache.fault);cases++;
 /* Full current-frame set cannot evict any already-referenced pattern. */
 reset();assert(nes_resident211_begin(&cache,1,true,1,empty_writer,NULL));
 struct nes_plan191 q={0};q.generation=1;q.kind=2;
 assert(nes_resident211_slot(&cache,&candidate,0,&q)==0);
 q.kind=0;q.mask=255;for(unsigned j=0;j<8;j++){q.alt[j]=UINT16_MAX;q.row[j*2]=q.row[j*2+1]=(uint8_t)j;}
 for(unsigned i=1;i<1024;i++){q.tag=(uint16_t)i;assert(nes_resident211_slot(&cache,&candidate,i,&q)==i);}
 q.tag=1024;assert(nes_resident211_slot(&cache,&candidate,1024,&q)==UINT16_MAX&&cache.fault);cases++;
 /* Destination B is older than last display A. A map group changed only in A
  * must still be copied into B when current-vs-display dirty mask is zero. */
 reset();assert(nes_resident211_begin(&cache,1,true,1,empty_writer,NULL));
 assert(nes_resident211_prepare(&cache,UINT64_MAX));assert(nes_resident211_commit(&cache,1,1,0,true));
 assert(nes_resident211_begin(&cache,1,true,2,empty_writer,NULL));
 assert(nes_resident211_prepare(&cache,0));assert(nes_resident211_commit(&cache,2,2,1,true));
 assert(nes_resident211_begin(&cache,1,true,3,empty_writer,NULL));
 assert(nes_resident211_prepare(&cache,UINT64_C(1)<<7));assert(cache.map_upload==(UINT64_C(1)<<7));
 assert(nes_resident211_commit(&cache,3,3,0,true));
 assert(nes_resident211_begin(&cache,1,true,4,empty_writer,NULL));
 assert(nes_resident211_prepare(&cache,0));assert(cache.map_upload==(UINT64_C(1)<<7));cases++;
 printf("FAULTS boundaries=%u active_preserved=1 mutable_refused=1\n",cases);
}
int main(void){
 for(unsigned i=0;i<64;i++)lut[i]=(uint16_t)(i*371);
 compatibility();scrolling();faults();
 printf("PASS RESIDENT211 frames=%u referenced_bytes=%u state_host_bytes=%u video_bytes=%u pattern_old=%u pattern_new=%u map_old=%u map_new=%u\n",
        frames,checked,(unsigned)sizeof cache,(unsigned)sizeof candidate,referencebytes,newbytes,reference_mapbytes,mapbytes);
 return 0;
}
