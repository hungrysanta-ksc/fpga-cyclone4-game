/* SPDX-License-Identifier: MIT */
/* Appended to the pinned receiver: reuse its logical_record validation and
 * tag enumeration. Outer transport CRC/token checks are not replaced here. */
#include "nes_delta231.h"
void nes_source231_reset(struct nes_source231 *d){memset(d,0,sizeof *d);}
static bool source_bad231(struct nes_source231 *d,struct nes_native165 *s){d->fault=true;d->valid=d->open=false;return fail(s,37);}
static uint8_t *source_byte231(struct nes_native165 *s,unsigned at){
 if(at<2112)return (uint8_t *)s->maps+at;
 at-=2112;
 if(at<224)return s->rows+at;
 at-=224;
 if(at<1024)return (uint8_t *)s->objects+at;
 at-=1024;
 if(at<512)return (uint8_t *)s->exceptions+at;
 at-=512;
 if(at<1792)return (uint8_t *)s->raster+at;
 at-=1792;
 if(at<64)return s->palette+at;
 at-=64;
 if(at<12)return (uint8_t *)s->counts+at;
 return &s->patch_count;
}
bool nes_source231_begin(struct nes_source231 *d,struct nes_native165 *s,uint32_t epoch,uint32_t base,uint32_t serial,uint16_t generation,bool full,unsigned spans,unsigned bytes){
 if(!d||!s)return false;
 if(d->fault||d->open||s->state!=NES_NATIVE165_IDLE||!serial||serial==UINT32_MAX||(!spans&&(full||bytes))||spans>5741||bytes>5741||
    (full?(base!=0):(base!=d->serial||!d->valid))||
    (d->valid&&(epoch!=d->epoch||serial!=d->serial+1))||(!d->valid&&(!full||serial!=1)))return source_bad231(d,s);
 d->epoch=epoch;d->pending=serial;d->generation=generation;d->open=true;d->full=full;d->geometry=false;
 d->next=d->end=d->spans=d->bytes=d->raw_at=0;d->want_spans=(uint16_t)spans;d->want_bytes=(uint16_t)bytes;return true;
}
bool nes_source231_write(struct nes_source231 *d,struct nes_native165 *s,unsigned sequence,unsigned at,const uint8_t *b,unsigned n){
 if(!d||!s)return false;
 if(d->fault||!d->open||d->geometry||sequence!=d->next||!b||!n||n>240||at<d->end||at>=5741||at+n>5741||
    (d->full&&at!=d->end)||d->spans>=d->want_spans||d->bytes+n>d->want_bytes)return source_bad231(d,s);
 for(unsigned i=0;i<n;i++)*source_byte231(s,at+i)=b[i];
 d->end=(uint16_t)(at+n);d->next++;d->spans++;d->bytes=(uint16_t)(d->bytes+n);return true;
}
static bool source_run231(struct nes_source231 *d,struct nes_native165 *s,unsigned sequence,unsigned at,unsigned n){
 if(d->fault||!d->open||d->full||!d->valid||d->geometry||sequence!=d->next||at<d->end||at+n>5741||
    d->spans>=d->want_spans||d->bytes+n>d->want_bytes)return source_bad231(d,s);
 d->end=(uint16_t)(at+n);d->next++;d->spans++;d->bytes=(uint16_t)(d->bytes+n);return true;
}
bool nes_source231_raster(struct nes_source231 *d,struct nes_native165 *s,unsigned sequence,unsigned at,unsigned rows,uint64_t mask){
 if(!d||!s)return false;
 if(at<3872||at>=5664||(at-3872)%8||!rows||rows>224||at+rows*8>5664||!mask)return source_bad231(d,s);
 if(!source_run231(d,s,sequence,at,rows*8))return false;
 for(unsigned i=0;i<rows;i++)s->raster[(at-3872)/8+i]^=mask;
 return true;
}
bool nes_source231_shift(struct nes_source231 *d,struct nes_native165 *s,unsigned sequence,unsigned at,int direction,uint16_t edge){
 if(!d||!s)return false;
 if(at>=2112||at%66||(direction!=1&&direction!=-1)||edge>32767)return source_bad231(d,s);
 if(!source_run231(d,s,sequence,at,66))return false;
 uint16_t *p=s->maps+at/2;
 if(direction==1){memmove(p,p+1,64);p[32]=edge;}
 else{memmove(p+1,p,64);p[0]=edge;}
 return true;
}
bool nes_source231_geometry(struct nes_source231 *d,struct nes_native165 *s){
 if(!d||!s)return false;
 if(d->fault||!d->open||d->geometry||d->spans!=d->want_spans||d->bytes!=d->want_bytes||(d->full&&d->end!=5741))return source_bad231(d,s);
 uint16_t counts[6];memcpy(counts,s->counts,sizeof counts);uint8_t patches=s->patch_count;
 if(!counts[0]||counts[0]>1056||counts[0]%33||counts[1]!=224||counts[2]>128||counts[3]>128||counts[4]!=224||
    (counts[5]!=32&&counts[5]!=64)||patches>7)return source_bad231(d,s);
 /* Geometry stays in place; invalidate raw union, rebuild requirements, then
  * refill raw only after META_END. No second geometry or framebuffer. */
 memset(s->required,0,sizeof s->required);
 memset((uint8_t *)s+offsetof(struct nes_native165,generation),0,sizeof(*s)-offsetof(struct nes_native165,generation));
 memcpy(s->counts,counts,sizeof counts);s->generation=d->generation;s->patch_count=patches;s->state=NES_NATIVE165_RECEIVING;s->last_tile=65535;
 for(unsigned k=0;k<6;k++)for(unsigned i=0;i<counts[k];i++){
  uint64_t v=k==0?s->maps[i]:k==1?s->rows[i]:k==2?s->objects[i]:k==3?s->exceptions[i]:k==4?s->raster[i]:s->palette[i];
  if(!logical_record(s,k,d->generation,i,v))return source_bad231(d,s);
 }
 if(!logical_record(s,7,d->generation,4,(uint64_t)s->records<<16))return source_bad231(d,s);
 d->geometry=true;return true;
}
bool nes_source231_raw(struct nes_source231 *d,struct nes_native165 *s,unsigned at,const uint8_t *b,unsigned n){
 if(!d||!s)return false;
 if(d->fault||!d->open||!d->geometry||at!=d->raw_at||!b||!n||n>240||at+n>s->patch_count*256u)return source_bad231(d,s);
 for(unsigned i=0;i<n;i++)if(!logical_record(s,6,d->generation,at+i,b[i]))return source_bad231(d,s);
 d->raw_at=(uint16_t)(at+n);return true;
}
bool nes_source231_end(struct nes_source231 *d,struct nes_native165 *s){
 if(!d||!s)return false;
 if(d->fault||!d->open||!d->geometry||d->raw_at!=s->patch_count*256u||
    !logical_record(s,7,d->generation,1,((uint64_t)s->records<<16)|s->bytes))return source_bad231(d,s);
 d->serial=d->pending;d->valid=true;d->open=false;return true;
}
