/* SPDX-License-Identifier: MIT */
#include "nes_delta231.h"
#include <string.h>
static void mark(struct nes_dirty231 *d,unsigned bit){
 if(!d||d->fault||!d->open||d->prepared||bit>=432){if(d)nes_dirty231_abort(d);return;}
 d->stale[0][bit/8]|=(uint8_t)(1u<<(bit%8));d->stale[1][bit/8]|=(uint8_t)(1u<<(bit%8));
}
void nes_dirty231_reset(struct nes_dirty231 *d){memset(d,0,sizeof *d);memset(d->stale,255,sizeof d->stale);}
void nes_dirty231_abort(struct nes_dirty231 *d){d->fault=true;d->open=d->prepared=d->valid=false;memset(d->stale,255,sizeof d->stale);}
bool nes_dirty231_begin(struct nes_dirty231 *d,const struct nes_resident211 *r){
 if(!d||!r)return false;
 if(d->fault||d->open||!r->open||r->prepared||r->fault||r->target>1||
    d->serial==UINT32_MAX||r->serial!=d->serial+1||r->displayed!=d->valid){nes_dirty231_abort(d);return false;}
 if(!d->valid||d->epoch!=r->epoch)memset(d->stale,255,sizeof d->stale);
 d->epoch=r->epoch;d->serial=r->serial;d->generation=r->generation;d->target=r->target;d->open=true;return true;
}
void nes_dirty231_map(struct nes_dirty231 *d,unsigned at){if(at>=4096){nes_dirty231_abort(d);return;}mark(d,at/16);}
uint8_t nes_dirty231_byte(const struct nes_native_video165 *p,unsigned section,unsigned at){
 if(section==2)return p->map[at];
 if(section==3)return p->cgram[at];
 if(at<2048)return p->patch.chr[at];
 at-=2048;
 if(at<162)return p->patch.mode[at/81][at%81];
 at-=162;
 if(at<81)return p->patch.enable[at];
 at-=81;
 return (uint8_t)(p->patch.size[at/2]>>(8*(at%2)));
}
static void changed(struct nes_dirty231 *d,const struct nes_native_video165 *p,unsigned section,unsigned at,const uint8_t *b,unsigned n){
 unsigned base=section==2?0:section==3?256:288;
 for(unsigned i=0;i<n;i++){
  unsigned bit=base+(at+i)/16,m=1u<<(bit%8);
  if((d->stale[0][bit/8]&m)&&(d->stale[1][bit/8]&m))continue;
  if(nes_dirty231_byte(p,section,at+i)!=b[i])mark(d,bit);
 }
}
/* Compare against last displayed material BEFORE bg_keys overwrites patch.
 * Only16B CHR scratch plus249B tables. The ordinary planner regenerates the
 * final material afterward; scratch is not mistaken for retained history. */
bool nes_dirty231_material(struct nes_dirty231 *d,const struct nes_native165 *s,const uint16_t *lut,const struct nes_native_video165 *p){
 if(!d||!d->open||d->prepared||d->fault||s->patch_count>7)return false;
 unsigned palettes=s->counts[5]/32;uint8_t block[16];
 for(unsigned at=0;at<512;at+=16){
  for(unsigned i=0;i<8;i++){
   unsigned word=at/2+i,v=0;
   if(word<palettes*16)v=lut[s->palette[(word/16)*32+word%16]];
   if(word>=128){unsigned q=word-128,e=q/64,a=q%64/16,c=q%16;if(e<palettes&&c<4)v=lut[s->palette[e*32+16+a*4+c]];}
   if(s->patch_count&&word>=64&&word<128)v=lut[word-64];
   block[i*2]=(uint8_t)v;block[i*2+1]=(uint8_t)(v>>8);
  }
  changed(d,p,3,at,block,16);
 }
 /* No-patch frames invalidate raw material for BOTH destinations. It may
  * become live again after the scratch was reused; never infer its base. */
 if(!s->patch_count){for(unsigned bit=288;bit<432;bit++)mark(d,bit);return !d->fault;}
 for(unsigned at=0;at<2048;at+=16){
  memset(block,0,sizeof block);unsigned x=(at/64)*8,plane=((at%64)/16)*2;
  for(unsigned slot=0;slot<s->patch_count;slot++)for(unsigned b=0;b<8;b++){
   unsigned c=64+s->raw_pixels[slot*256+x+b];
   block[slot*2]|=(uint8_t)(((c>>plane)&1)<<(7-b));
   block[slot*2+1]|=(uint8_t)(((c>>(plane+1))&1)<<(7-b));
  }
  changed(d,p,5,at,block,16);
 }
 uint8_t tables[249]={0};unsigned offset=0;
 unsigned first=0;while(first<224&&((s->raster[first]>>49)&1))first++;
 if(first==224)return false;
 unsigned mask=(unsigned)(s->raster[first]>>36)&255;
 for(unsigned y=0;y<224;){
  bool raw=((s->raster[y]>>49)&1)!=0;unsigned n=y+1;
  while(n<224&&n-y<127&&(((s->raster[n]>>49)&1)!=0)==raw)n++;
  if(offset+6>81)return false;
  for(unsigned bank=0;bank<2;bank++){
   uint8_t *t=tables+bank*81+offset;t[0]=(uint8_t)(n-y);t[1]=raw?3:0;t[3]=(uint8_t)((raw?0x38:0x31)+bank*0x20);
  }
  uint8_t *t=tables+162+offset;t[0]=(uint8_t)(n-y);t[1]=raw?1:17;t[3]=!raw&&mask==0x18?17:0;
  offset+=5;y=n;
 }
 for(unsigned i=0;i<3;i++)tables[243+i*2]=(uint8_t)(offset+1);
 changed(d,p,5,2048,tables,sizeof tables);return !d->fault;
}
bool nes_dirty231_commit(struct nes_dirty231 *d,uint32_t serial,uint16_t generation,unsigned bank,bool visible){
 if(!d||d->fault)return false;
 if(!d->open||!d->prepared||!visible||serial!=d->serial||generation!=d->generation||bank!=d->target){nes_dirty231_abort(d);return false;}
 /* A no-patch frame does not establish any raw destination. Its stale bits
  * are retained by the caller via prepare mask, before this commit. */
 memset(d->stale[bank],0,36); /* map32 + CGRAM4 */
 if(d->raw)memset(d->stale[bank]+36,0,18);
 d->valid=true;d->open=d->prepared=false;return true;
}
