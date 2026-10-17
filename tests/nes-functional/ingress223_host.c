/* SPDX-License-Identifier: MIT */
#include "nes_native165.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
void baseline_reset(struct nes_native165 *);
bool baseline_packet(struct nes_native165 *,uint16_t,const uint8_t *,unsigned);
typedef bool (*packet_fn)(struct nes_native165 *,uint16_t,const uint8_t *,unsigned);
static unsigned width(unsigned k,unsigned index,int packed){
 static const unsigned w[]={2,1,7,4,7,1,2,8};
 return packed&&k==0&&(index&0x1000)?8:w[k];
}
static void accept(struct nes_native165 *s){
 /* Consumer PREPARED is a fixture here. Actual serial D3 is tested separately. */
 assert(s->state==NES_NATIVE165_COMPLETE);s->state=NES_NATIVE165_PREPARED;
}
static unsigned wire(const char *name,struct nes_native165 *s,packet_fn fn,int packed){
 FILE *f=fopen(name,"r");assert(f);unsigned hi,mid,lo,token=0,bytes=0;
 while(fscanf(f,"%8x%8x%8x",&hi,&mid,&lo)==3){
  unsigned k=hi>>29,gen=(hi>>13)&65535,index=hi&8191,w=width(k,index,packed);
  uint64_t v=((uint64_t)mid<<32)|lo;uint8_t b[12];unsigned tag=(k<<13)|index;
  b[0]=tag>>8;b[1]=tag;b[2]=gen>>8;b[3]=gen;
  for(unsigned i=0;i<w;i++)b[4+i]=(uint8_t)(v>>(8*(w-1-i)));
  if(k==7&&index==3&&s->state!=NES_NATIVE165_FAILED)accept(s);
  if(s->state!=NES_NATIVE165_FAILED)(void)fn(s,(uint16_t)token,b,w+4);
  token++;bytes+=w+4;
 }
 fclose(f);return bytes;
}
static uint16_t crc16(const uint8_t *p,unsigned n){
 uint16_t c=65535;while(n--){c^=(uint16_t)*p++<<8;for(unsigned i=0;i<8;i++)c=(uint16_t)((c<<1)^((c&0x8000)?0x1021:0));}return c;
}
static unsigned serial(const char *name,struct nes_native165 *s){
 FILE *f=fopen(name,"r");assert(f);unsigned n,blocks=0;uint8_t tx[259],rx[259];
 while(fscanf(f,"%u",&n)==1){
  assert(n<=259);unsigned v;
  for(unsigned i=0;i<n;i++){assert(fscanf(f,"%2x",&v)==1);tx[i]=(uint8_t)v;}
  for(unsigned i=0;i<n;i++){assert(fscanf(f,"%2x",&v)==1);rx[i]=(uint8_t)v;}
  if(tx[0]==0xd1){assert(n>3);assert(crc16(rx+1,n-3)==(uint16_t)((rx[n-2]<<8)|rx[n-1]));
   assert(nes_native165_packet(s,(uint16_t)blocks,rx+1,n-3));blocks++;
  }else if(tx[0]==0xd3){assert(tx[4]==1);accept(s);}
 }
 fclose(f);assert(s->state==NES_NATIVE165_COMMITTED);return blocks;
}
static void begin(struct nes_native165 *s){
 uint64_t v=(UINT64_C(0x2231)<<48)|(UINT64_C(1)<<42)|(UINT64_C(1)<<36)|(UINT64_C(224)<<28);
 uint8_t b[12]={0xe0,0,0,12};for(unsigned i=0;i<8;i++)b[4+i]=(uint8_t)(v>>(56-8*i));
 nes_native165_reset(s);assert(nes_native165_packet(s,0,b,12));
}
static void faults(void){
 struct nes_native165 s;unsigned cases=0;
 for(unsigned fault=0;fault<13;fault++){
  begin(&s);uint8_t b[12]={0x10,0,0,12,0x40,0,0,0,0,0,0,1};unsigned len=12,tok=1;
  switch(fault){
   case 0:b[1]=1;break; /* wrong start */
   case 1:b[4]=0;break; /* zero count */
   case 2:b[4]=0x50;break; /* count5 */
   case 3:b[4]=0x30;break; /* non-final short group */
   case 4:b[3]^=1;break;
   case 5:len=11;break;
   case 6:tok=2;break;
   case 7:s.next_kind=7;break;
   case 8:s.counts[0]=1;b[4]=0x10;b[9]=1;break; /* padding above15bits */
   case 9:s.at[0]=33;break;
   case 10:s.state=NES_NATIVE165_COMMITTED;break;
   case 11:b[0]=0x18;break; /* reserved large index */
   case 12:assert(nes_native165_packet(&s,1,b,12));tok=2;break; /* duplicate */
  }
  assert(!nes_native165_packet(&s,(uint16_t)tok,b,len));assert(s.state==NES_NATIVE165_FAILED);
  assert(!nes_native181_pixels(&s,0));cases++;
 }
 begin(&s);uint8_t old[12]={0xe0,0,0,12,0x20,0x31};nes_native165_reset(&s);
 assert(!nes_native165_packet(&s,0,old,12));cases++;
 printf("PASS INGRESS223 faults=%u receiver_bytes=%u\n",cases,(unsigned)sizeof s);
}
int main(int argc,char **argv){
 assert(argc==4);struct nes_native165 old,now;baseline_reset(&old);nes_native165_reset(&now);
 unsigned a=wire(argv[1],&old,baseline_packet,0),b;
 if(!strcmp(argv[3],"serial"))b=serial(argv[2],&now);
 else b=wire(argv[2],&now,nes_native165_packet,1);
 old.next_token=now.next_token=0;old.token_valid=now.token_valid=false;
 assert(!memcmp(&old,&now,sizeof old));
 printf("PASS INGRESS223 exact state=%u baseline_bytes=%u candidate_bytes_or_blocks=%u\n",now.state,a,b);
 faults();return 0;
}
