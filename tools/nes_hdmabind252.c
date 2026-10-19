/* SPDX-License-Identifier: MIT */
/* Pre-send certificate candidate. No transport, IRQ or FPGA binding implied. */
#include "nes_native_video165.h"
bool nes_hdma251_validate(const struct nes_native_video165 *);
static void put16(uint8_t *p,unsigned v){p[0]=v;p[1]=v>>8;}
static void put32(uint8_t *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=v>>(8*i);}
static uint16_t crc(uint16_t c,const uint8_t *p,unsigned n){
 while(n--){c^=(uint16_t)*p++<<8;for(unsigned i=0;i<8;i++)c=c&0x8000?(uint16_t)(c<<1)^0x1021:(uint16_t)(c<<1);}
 return c;
}
bool nes_hdmabind252_prepare(const struct nes_native_video165 *p,uint32_t epoch,
 uint32_t serial,uint32_t display_base,uint8_t bank,uint8_t out[32]){
 if(!p||!out||!p->valid||!epoch||!serial||serial==UINT32_MAX||display_base>=serial||bank>1||bank!=((serial-1)&1)||!nes_hdma251_validate(p))return false;
 for(unsigned i=0;i<32;i++)out[i]=0;
 out[0]='H';out[1]='2';out[2]=1;out[3]=bank;
 put32(out+4,epoch);put32(out+8,serial);put16(out+12,p->generation);put16(out+14,p->hdma_size);
 out[19]=p->display_mask;out[20]=p->patch_count;
 uint16_t c=crc(0xffff,p->hdma,p->hdma_size);unsigned total=p->hdma_size;
 if(p->patch_count){
  for(unsigned i=0;i<3;i++)out[16+i]=p->patch.size[i];
  c=crc(c,p->patch.mode[0],p->patch.size[0]);c=crc(c,p->patch.mode[1],p->patch.size[1]);c=crc(c,p->patch.enable,p->patch.size[2]);
  total+=p->patch.size[0]+p->patch.size[1]+p->patch.size[2]+6;
  for(unsigned i=0;i<3;i++){uint8_t b[2];put16(b,p->patch.size[i]);c=crc(c,b,2);}
 }
 put16(out+22,c);put16(out+24,total);put32(out+26,display_base);put16(out+30,crc(0xffff,out,30));return true;
}
bool nes_hdmabind252_shadow(const struct nes_native_video165 *p,uint32_t epoch,
 uint32_t serial,uint32_t display_base,uint8_t bank,uint8_t out[32]){
 /* Reuse the semantic/certificate admission; recomputing fresh digest here
  * is deliberately charged in this reference, not claimed optimized away. */
 if(!nes_hdmabind252_prepare(p,epoch,serial,display_base,bank,out))return false;
 uint16_t c=crc(0xffff,p->hdma,p->hdma_size),block=0xffff;
 if(p->patch_count)for(unsigned i=0;i<249;i++){
  uint8_t v=i<81?p->patch.mode[0][i]:i<162?p->patch.mode[1][i-81]:i<243?p->patch.enable[i-162]:(uint8_t)(p->patch.size[(i-243)/2]>>(8*((i-243)%2)));
  block=crc(block,&v,1);
  if(i%16==15||i==248){uint8_t b[2];put16(b,block);c=crc(c,b,2);block=0xffff;}
 }
 out[2]=2;put16(out+22,c);put16(out+24,p->hdma_size+(p->patch_count?249:0));put16(out+30,crc(0xffff,out,30));return true;
}
