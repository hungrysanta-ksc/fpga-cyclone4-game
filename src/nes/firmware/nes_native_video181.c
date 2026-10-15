/* SPDX-License-Identifier: MIT */
/*181 Candidate; materialize with the paired header as video165. */
#include "nes_native_video165.h"
#include <string.h>
static bool fail(struct nes_native_video165 *p,unsigned e){p->valid=false;p->error=(uint8_t)e;return false;}
static void put16(uint8_t *p,unsigned v){p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);}
static const uint8_t *tile(const struct nes_native165 *s,unsigned tag,unsigned kind){
 for(unsigned i=0;i<s->ntiles;i++)if(s->tiles[i].tag==tag&&(s->tiles[i].kind&kind))return s->tiles[i].data;
 return NULL;
}
static bool patched(const struct nes_native165 *s,unsigned y){return ((s->raster[y]>>49)&1)!=0;}
static unsigned epoch(const struct nes_native165 *s,unsigned y){return(unsigned)(s->raster[y]>>44)&31;}
static unsigned fine(const struct nes_native165 *s,unsigned y,unsigned x,bool low){
 for(unsigned i=0;i<s->counts[3];i++){
  uint32_t v=s->exceptions[i];if(((v>>6)&8191)==y*33+x)return(v>>(low?0:3))&7;
 }
 return s->rows[y]&7;
}
static unsigned bg_slot(struct nes_native_video165 *p,uint64_t key){
 for(unsigned i=1;i<p->bg_count;i++)if(p->bg_keys[i]==key)return i;
 if(p->bg_count==1024)return 1024;
 p->bg_keys[p->bg_count]=key;return p->bg_count++;
}
static unsigned obj_slot(struct nes_native_video165 *p,uint32_t key){
 for(unsigned i=0;i<p->obj_count;i++)if(p->obj_keys[i]==key)return i;
 if(p->obj_count==128)return 128;
 p->obj_keys[p->obj_count]=key;return p->obj_count++;
}
bool nes_native_video165_build(const struct nes_native165 *s,const uint16_t lut[64],struct nes_native_video165 *p,nes_native_video165_stage_fn stage,void *ctx){
 if(!s||!lut||!p||!stage)return false;
 memset(p,0,sizeof(*p));p->generation=s->generation;
 if(s->state!=NES_NATIVE165_COMMITTED||s->counts[0]==0||s->counts[0]>1056||s->counts[0]%33||
  s->counts[1]!=224||s->counts[2]>128||s->counts[3]>128||s->counts[4]!=224||
  (s->counts[5]!=32&&s->counts[5]!=64)||s->ntiles>512)return fail(p,1);
 unsigned palettes=s->counts[5]/32;
 if(s->patch_count>7)return fail(p,15);
 p->patch_count=s->patch_count;
 unsigned first_normal=0;while(first_normal<224&&patched(s,first_normal))first_normal++;
 if(first_normal==224)return fail(p,15);
 p->display_mask=(uint8_t)(s->raster[first_normal]>>36);
 if(p->display_mask!=0x1e && p->display_mask!=0x18)return fail(p,3);
 for(unsigned i=0;i<s->counts[5];i++)if(s->palette[i]>=64)return fail(p,2);
 if(palettes==2&&s->palette[0]!=s->palette[32])return fail(p,2);
 unsigned raw_count=0;
 for(unsigned y=0;y<224;y++){
  if(patched(s,y)){
   if(s->raster[y]>>53||(s->raster[y]&((UINT64_C(1)<<49)-1))||((s->raster[y]>>50)&7)!=raw_count||raw_count>=s->patch_count)return fail(p,15);
   const uint8_t *pixels=nes_native181_pixels(s,raw_count++);if(!pixels)return fail(p,15);
   for(unsigned x=0;x<256;x++)if(pixels[x]>=64)return fail(p,15);
  }else if(s->raster[y]>>49||(s->rows[y]>>3)>=s->counts[0]/33||epoch(s,y)>=palettes||((s->raster[y]>>36)&255)!=p->display_mask)return fail(p,3);
 }
 if(raw_count!=s->patch_count)return fail(p,15);
 for(unsigned i=0;i<s->counts[3];i++){
  unsigned v=s->exceptions[i];if(((v>>6)&8191)>=7392||patched(s,((v>>6)&8191)/33))return fail(p,4);
  for(unsigned j=0;j<i;j++)if(((s->exceptions[j]>>6)&8191)==((v>>6)&8191))return fail(p,4);
 }
 /* Regroup compact rows when the palette or column-zero fine Y changes.
  * Each SNES group maps at most eight consecutive destination fine rows. */
 uint8_t first[32],end[32],bank[32];unsigned groups=0;
 for(unsigned y=0;y<224;y++){
  if(patched(s,y)){
   p->hofs[y]=0;p->vofs[y]=(uint16_t)((((s->raster[y]>>50)&7)-y-1)&1023);continue;
  }
  unsigned g=s->rows[y]>>3,fy=fine(s,y,0,false),e=epoch(s,y);
  bool split=y==0||fy==0||(y&&patched(s,y-1));
  if(y&&!patched(s,y-1))split=split||fy!=fine(s,y-1,0,false)+1||e!=epoch(s,y-1)||memcmp(&s->maps[g*33],&s->maps[(s->rows[y-1]>>3)*33],66)!=0;
  if(split){if(groups==32)return fail(p,5);first[groups]=(uint8_t)y;bank[groups]=(uint8_t)e;groups++;}
  end[groups-1]=(uint8_t)(y+1);p->hofs[y]=(uint16_t)((s->raster[y]>>30)&7);
  p->vofs[y]=(uint16_t)(((groups-1)*8+fy-y-1)&1023);
 }
 p->groups=(uint8_t)groups;p->bg_count=1;
 /* Slot0 is already zero in OAM scratch. Flush15 contiguous BG tiles
  * per packet. OAM has no sprite contents until this phase completes. */
 for(unsigned g=0;g<groups;g++)for(unsigned x=0;x<33;x++){
  unsigned cell=s->maps[(s->rows[first[g]]>>3)*33+x];if(cell>>15)return fail(p,6);
  const uint8_t *src=tile(s,cell&8191,1);if(!src)return fail(p,6);
  uint8_t b[16],mapping[16];for(unsigned f=0;f<8;f++){mapping[f*2]=(uint8_t)f;mapping[f*2+1]=(uint8_t)f;}
  for(unsigned y=first[g];y<end[g];y++){
   unsigned dest=fine(s,y,0,false);mapping[dest*2]=(uint8_t)fine(s,y,x,true);mapping[dest*2+1]=(uint8_t)fine(s,y,x,false);
  }
  uint64_t key=cell&8191;for(unsigned f=0;f<16;f++){key|=(uint64_t)mapping[f]<<(13+f*3);b[f]=src[mapping[f]+((f&1)?8:0)];}
  /* Cross-tile cells use a unique per-frame key. Never hash pixel bytes or
   * silently alias another pattern; ordinary patterns retain exact dedupe. */
  for(unsigned i=0;i<s->counts[3];i++){
   uint32_t e=s->exceptions[i];unsigned pos=(e>>6)&8191,y=pos/33;
   if(pos%33==x && y>=first[g] && y<end[g] && (e>>19)!=(cell&8191)){
    const uint8_t *lo=tile(s,e>>19,1);if(!lo)return fail(p,6);
    b[fine(s,y,0,false)*2]=lo[e&7];key=(UINT64_C(1)<<63)|(g*33+x);
   }
  }
  unsigned previous=p->bg_count,slot=bg_slot(p,key);if(slot==1024)return fail(p,7);
  if(slot==previous){
   memcpy(p->oam+(slot%15)*16,b,16);
   if(slot%15==14&&!stage(ctx,0,slot-14,p->oam,240))return fail(p,14);
  }
  unsigned at=((x/32)*1024+g*32+x%32)*2;
  put16(p->map+at,slot|((bank[g]*4+(cell>>13))<<10)|0x2000);
 }
 if(p->bg_count%15&&!stage(ctx,0,p->bg_count-p->bg_count%15,p->oam,(p->bg_count%15)*16))return fail(p,14);
 /* No callback retains scratch pointers; only ACKed tentative bytes persist.
  * Clear all544 bytes, including high-OAM, before changing its lifetime. */
 memset(p->oam,0,sizeof(p->oam));
 for(unsigned i=0;i<128;i++)p->oam[i*4+1]=240;
 uint8_t rank_used[224]={0},evaluation[224]={0};
 /* Compact fragments already carry stable NES evaluation rank. Sorting by
  * rank preserves every visible row; same-rank visible overlaps are rejected. */
 for(unsigned rank=0;rank<8;rank++)for(unsigned i=0;i<s->counts[2];i++){
  uint64_t v=s->objects[i];if(v>>49)return fail(p,8);if(((v>>46)&7)!=rank)continue;
  unsigned tag=(unsigned)v&8191,x=(unsigned)(v>>22)&255,attr=(unsigned)(v>>30)&255,mask=(unsigned)(v>>38)&255;
  int top=(int)((v>>13)&511);if(top&256)top-=512;if(!mask)return fail(p,8);
  const uint8_t *src=tile(s,tag,2);if(!src)return fail(p,9);
  uint8_t masks[2]={0};
  for(unsigned f=0;f<8;f++)if(mask&(1u<<f)){
   int y=top+((attr&128)?7-(int)f:(int)f);if(y<0||y>=224)return fail(p,10);
   if(patched(s,(unsigned)y))continue;
   if(rank_used[y]&(1u<<rank))return fail(p,10);
   rank_used[y]|=(uint8_t)(1u<<rank);masks[epoch(s,(unsigned)y)]|=(uint8_t)(1u<<f);
  }
  for(unsigned e=0;e<palettes;e++)if(masks[e]){
   if(p->objects==128)return fail(p,11);
   for(int y=top;y<top+8;y++)if(y>=0&&y<224&&!patched(s,(unsigned)y)&&++evaluation[y]>32)return fail(p,12);
   uint8_t b[32]={0};for(unsigned f=0;f<8;f++)if(masks[e]&(1u<<f)){b[f*2]=src[f];b[f*2+1]=src[f+8];}
   unsigned previous=p->obj_count,slot=obj_slot(p,tag|((unsigned)masks[e]<<13));if(slot==128)return fail(p,13);
   if(slot==previous){
    memcpy(p->cgram+(slot%7)*32,b,32);
    if(slot%7==6&&!stage(ctx,1,slot-6,p->cgram,224))return fail(p,14);
   }
   unsigned o=p->objects++*4;p->oam[o]=(uint8_t)x;p->oam[o+1]=(uint8_t)top;p->oam[o+2]=(uint8_t)slot;
   p->oam[o+3]=(uint8_t)(((e*4+(attr&3))<<1)|((attr&32)?0x20:0x30)|(attr&0xc0));
  }
 }
 if(p->obj_count%7&&!stage(ctx,1,p->obj_count-p->obj_count%7,p->cgram,(p->obj_count%7)*32))return fail(p,14);
 /* CGRAM becomes the palette only after the final OBJ ACK. */
 memset(p->cgram,0,sizeof(p->cgram));
 put16(p->cgram,lut[s->palette[0]]);
 for(unsigned e=0;e<palettes;e++)for(unsigned a=0;a<4;a++)for(unsigned c=0;c<4;c++){
  put16(p->cgram+(e*16+a*4+c)*2,lut[s->palette[e*32+a*4+c]]);
  put16(p->cgram+(128+e*64+a*16+c)*2,lut[s->palette[e*32+16+a*4+c]]);
 }
 unsigned at=0;
 for(unsigned y=0;y<224;){
  unsigned n=y+1;while(n<224&&n-y<127&&p->hofs[n]==p->hofs[y]&&p->vofs[n]==p->vofs[y])n++;
  p->hdma[at++]=(uint8_t)(n-y);put16(p->hdma+at,p->hofs[y]);put16(p->hdma+at+2,p->vofs[y]);at+=4;y=n;
 }
 p->hdma[at++]=0;p->hdma_size=(uint16_t)at;
 if(p->patch_count){
  /* No BG allocation uses the keys after this point. All eight fine rows
   * start zero; retained slots0..6 receive the already-composited NES color. */
  memset(&p->patch,0,sizeof(p->patch));
  for(unsigned slot=0;slot<p->patch_count;slot++){
   const uint8_t *pixels=nes_native181_pixels(s,slot);
   for(unsigned x=0;x<256;x++)for(unsigned plane=0;plane<8;plane++)
    p->patch.chr[(x/8)*64+(plane/2)*16+slot*2+plane%2]|=(uint8_t)((((64+pixels[x])>>plane)&1)<<(7-x%8));
  }
  for(unsigned c=0;c<64;c++)put16(p->cgram+(64+c)*2,lut[c]);
  /* <=7 raw rows produce <=15 alternating runs:plus one127-split:16*(count+4)+end=81.
   * A/B map tables are selected by the SNES at the final bank flip.
   * TM/TS/TMW/TSW also disables the left8 window on composed raw rows. */
  unsigned offset=0;
  for(unsigned y=0;y<224;){
   bool raw=patched(s,y);unsigned n=y+1;
   while(n<224&&n-y<127&&patched(s,n)==raw)n++;
   if(offset+6>81)return fail(p,16);
   for(unsigned b=0;b<2;b++){
    uint8_t *t=p->patch.mode[b]+offset;t[0]=(uint8_t)(n-y);t[1]=raw?3:0;t[2]=0;t[3]=(uint8_t)((raw?0x38:0x31)+b*0x20);t[4]=0;
   }
   uint8_t *t=p->patch.enable+offset;t[0]=(uint8_t)(n-y);t[1]=raw?1:17;t[2]=0;t[3]=!raw&&p->display_mask==0x18?17:0;t[4]=0;
   offset+=5;y=n;
  }
  for(unsigned i=0;i<3;i++)p->patch.size[i]=(uint16_t)(offset+1);
 }
 p->valid=true;return true;
}
