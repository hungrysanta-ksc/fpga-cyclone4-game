/* SPDX-License-Identifier: MIT */
/* Feasibility component, not wired into the live firmware. The test arrays
 * model a streaming callback; their7168B output storage is not a RAM saving. */
#include <stdint.h>
extern uint8_t bits393[256],map393[4096],jobs393[3072],payload393[4096];
extern uint32_t info393[8];
static uint32_t columns393[64];
static unsigned bit393(unsigned w){return (bits393[w>>3]>>(w&7))&1;}
static void w16_393(uint8_t *p,unsigned x){p[0]=x;p[1]=x>>8;}
static void emit393(unsigned first,unsigned n,unsigned stride,unsigned bank){
 unsigned at=info393[0]++,off=info393[3];uint8_t *p=jobs393+12*at;
 w16_393(p,(bank?0x5000:0x3000)|first);w16_393(p+2,0xc000+off);w16_393(p+4,n*2);
 p[6]=4|(stride==32?32:0);p[7]=0x7e;p[8]=stride==32?0x81:0x80;p[9]=2;w16_393(p+10,first);
 for(unsigned i=0;i<n;i++){unsigned w=first+i*stride;payload393[off++]=map393[w*2];payload393[off++]=map393[w*2+1];}
 info393[3]=off;
}
unsigned build_jobs393(unsigned policy,unsigned bank){
 unsigned rows=0,cols=0,words=0,previous=4096;
 for(unsigned i=0;i<8;i++)info393[i]=0;
 if(policy>2||bank>1)return 0;
 for(unsigned i=0;i<64;i++)columns393[i]=0;
 for(unsigned g=0;g<256;g++){
  unsigned b=bits393[g];
  while(b){unsigned i=__builtin_ctz(b),w=g*8+i;b&=b-1;
   if(w!=previous+1)rows++;previous=w;words++;
   columns393[(w&31)+(w>>10)*32]|=UINT32_C(1)<<((w>>5)&31);
  }
 }
 for(unsigned c=0;c<64;c++){unsigned m=columns393[c];m&=~(m<<1);while(m){cols++;m&=m-1;}}
 unsigned mode=policy<2?policy:cols<rows;
 info393[1]=words;info393[2]=mode;info393[4]=rows;info393[5]=cols;
 if((mode?cols:rows)>256)return 0;
 if(mode){
  for(unsigned c=0;c<64;c++){
   uint32_t m=columns393[c];
   while(m){unsigned lo=__builtin_ctz(m),n=0;
    while(lo+n<32&&(m&(UINT32_C(1)<<(lo+n)))){m&=~(UINT32_C(1)<<(lo+n));n++;}
    emit393((c>>5)*1024+lo*32+(c&31),n,32,bank);
   }
  }
 }else{
  unsigned w=0;
  while(w<2048){if(!(w&7)&&!bits393[w>>3]){w+=8;continue;}if(!bit393(w)){w++;continue;}unsigned first=w;do{w++;}while(w<2048&&bit393(w));emit393(first,w-first,1,bank);}
 }
 info393[6]=3328+1280*info393[0]+16*words;return 1;
}
