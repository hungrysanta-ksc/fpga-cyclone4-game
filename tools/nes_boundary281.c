/* SPDX-License-Identifier: MIT
 * Cost probes only: no live SPI, firmware integration or trusted receipt.
 * Caller retains original command until ACK; normalized spans are hints.
 */
#include <stdint.h>
static unsigned u16(const uint8_t *p){return p[0]|((unsigned)p[1]<<8);}
static void w16(uint8_t *p,unsigned n){p[0]=n;p[1]=n>>8;}
static unsigned span(uint8_t *out,unsigned first,unsigned count){
 if(!count||first+count>1328)return 0xffffffffu;
 w16(out,first);w16(out+2,count);return 1;
}
unsigned spans281(const uint8_t *p,unsigned n,uint8_t *out,unsigned context){
 if(n<16||n!=16+u16(p+12))return 0xffffffffu;
 unsigned op=p[0],sec=p[1],at=u16(p+10),plen=u16(p+12);
 unsigned len=op==2?plen:u16(p+14),end=at+len;
 unsigned scroll=context&65535,raw=context>>16;
 if(raw>2||scroll>1121||!scroll||!len)return 0xffffffffu;
 if(op==7){
  unsigned unit=sec?32:16,limit=sec?4096:16384;
  if(sec>1||plen!=4||len>2048||at%unit||len%unit||end>limit)return 0xffffffffu;
  return span(out,(sec?1024:0)+at/unit,len/unit);
 }
 if(op!=2&&op!=4&&op!=5&&op!=8)return 0xffffffffu;
 if(op!=2&&(plen!=(op==8?4u:2u)||len%plen))return 0xffffffffu;
 if(sec==3){if(end>512||at%16||len%16)return 0xffffffffu;return span(out,1152+at/16,len/16);}
 if(sec==4)return end<=544?0:0xffffffffu;
 if(sec!=5||end>3418||(at<scroll&&(at||end<scroll)))return 0xffffffffu;
 if(end>3169&&((at>3169&&(at-3169)%16)||(end!=3418&&(end-3169)%16)))return 0xffffffffu;
 unsigned count=0,lo=at<1121?1121:at,hi=end>3169?3169:end;
 if(lo<hi){
  if((lo-1121)%16||(hi-1121)%16)return 0xffffffffu;
  count=span(out,1184+(lo-1121)/16,(hi-lo)/16);
 }
 if(raw&&end>3169){
  lo=at<3169?3169:at;
  span(out+4*count,1312+(lo-3169)/16,(end-lo+15)/16);count++;
 }
 return count;
}
unsigned manifest281(const uint8_t *p,unsigned n,uint8_t *out,unsigned at){
 if(n<16||n!=16+u16(p+12)||p[1]!=2||u16(p+10)!=at||u16(p+14)||at>256)return 0xffffffffu;
 unsigned pos=16;
 if(p[0]==10){
  if(n==16||n-16>256-at)return 0xffffffffu;
  while(pos<n)out[at++]=p[pos++];
 }else if(p[0]==11){
  if(n<18||p[pos++]!=3)return 0xffffffffu;
  while(pos<n){
   unsigned tag=p[pos++],take=(tag&127)+1;
   if(take>256-at||(!(tag&128)&&take>n-pos))return 0xffffffffu;
   while(take--)out[at++]=(tag&128)?0:p[pos++];
  }
 }else return 0xffffffffu;
 return at;
}
unsigned wire281(const uint8_t *p,unsigned n,uint8_t *out,unsigned compact){
 if(n<16||n>256||n!=16+u16(p+12)||compact>1)return 0;
 unsigned at=1;out[0]=0xe1;
 for(unsigned i=0;i<n;i++){
  if(compact&&(i==8||i==9||i==12||i==13))continue;
  out[at++]=p[i];
 }
 unsigned c=65535;
 for(unsigned i=0;i<at;i++){
  c^=(unsigned)out[i]<<8;
  for(unsigned j=0;j<8;j++)c=(c&32768)?(c<<1)^0x1021:c<<1;
 }
 out[at++]=c>>8;out[at++]=c;return at;
}
