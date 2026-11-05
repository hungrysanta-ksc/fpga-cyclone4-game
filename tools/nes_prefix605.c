/* Diagnostic selector: no resident mutation and no slot assignment. */
#include "nes_resident211.h"
struct selector605 {
 uint8_t seen[1024];
 uint16_t cursor, tags[3], generation, count;
 uint32_t epoch;
};

unsigned init605(struct selector605 *s,const struct nes_resident211 *r,unsigned gen){
 if(!r->displayed||r->fault||r->open||r->prepared||!r->epoch||r->bg_slots>1024)return 0;
 for(unsigned j=0;j<sizeof s->seen;j++)s->seen[j]=0;
 const uint8_t *valid=r->resident[!r->active];
 for(unsigned i=1;i<r->bg_slots;i++){
  unsigned tag=r->bg[i];
  if(tag<8192 && (valid[i/8]&(1u<<(i%8))))s->seen[tag/8]|=1u<<(tag%8);
 }
 s->epoch=r->epoch;s->generation=gen;s->cursor=0;s->count=0;return 1;
}

/* Called only after successful D1 parse and D2 retirement confirmation.
 * A selected tag can only populate temporary immutable-ROM data. */
unsigned offer605(struct selector605 *s,const uint16_t *map,unsigned end,uint8_t wire[17]){
 if(end>1056||end<s->cursor||s->count==3)return 0;
 while(s->cursor<end){
  unsigned tag=map[s->cursor++]&8191, bit=1u<<(tag%8);
  if(s->seen[tag/8]&bit)continue;
  s->seen[tag/8]|=bit;s->tags[s->count++]=tag;
  if(s->count==3){
   wire[0]=0x61;wire[1]=3;
   for(unsigned i=0;i<4;i++)wire[2+i]=s->epoch>>(8*i);
   wire[6]=s->generation;wire[7]=s->generation>>8;
   for(unsigned i=0;i<3;i++){wire[8+2*i]=s->tags[i];wire[9+2*i]=s->tags[i]>>8;}
   unsigned crc=65535;
   for(unsigned i=0;i<14;i++){
    unsigned x=(crc>>8)^wire[i];x^=x>>4;crc=((crc<<8)^(x<<12)^(x<<5)^x)&65535;
   }
   wire[14]=crc>>8;wire[15]=crc;wire[16]=0xa5;return 1;
  }
 }
 return 0;
}
