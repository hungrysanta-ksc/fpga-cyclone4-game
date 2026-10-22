/* SPDX-License-Identifier: MIT */
/* Executed Cortex-M4 output serializer. io259 is the synchronous SPI driver
 * boundary, not an STM32 peripheral/IRQ timing model. Input is a pinned plan. */
#include <stdint.h>
extern int io259(uint8_t *inout,unsigned length);
extern void trace259(unsigned event,unsigned value);
struct state259 {uint16_t sent,retired,sequence,generation;uint32_t serial,token;uint8_t bank,error;};
struct state259 state259;
const uint8_t *material259; /* caller-owned planner metadata: map/CGRAM/OAM/HDMA */
static uint8_t wire259[259],status259[24];
static unsigned u16(const uint8_t *p){return p[0]|(unsigned)p[1]<<8;}
static uint32_t u32(const uint8_t *p){return u16(p)|(uint32_t)u16(p+2)<<16;}
static void w16(uint8_t *p,unsigned v){p[0]=v;p[1]=v>>8;}
static void w32(uint8_t *p,uint32_t v){w16(p,v);w16(p+2,v>>16);}
static unsigned fail(unsigned e){if(!state259.error)state259.error=e;return 0;}
static unsigned crc8(unsigned c,unsigned b){c^=b;for(unsigned i=0;i<8;i++)c=(c&128)?(c<<1)^7:c<<1;return c&255;}
static unsigned crc16(unsigned c,unsigned b){c^=b<<8;for(unsigned i=0;i<8;i++)c=(c&32768)?(c<<1)^0x1021:c<<1;return c&65535;}
static unsigned status(void){
 if(state259.error)return 0;
 for(unsigned i=0;i<24;i++)status259[i]=0;status259[0]=0xe0;
 if(!io259(status259,24))return fail(1);
 unsigned c=0;for(unsigned i=1;i<23;i++)c=crc8(c,status259[i]);
 if(status259[1]!=0xf8||status259[23]!=c||(status259[2]&0xf8))return fail(2);
 unsigned a=(status259[3]<<8)|status259[4],r=(status259[5]<<8)|status259[6];
 unsigned pending=(uint16_t)(state259.sent-state259.retired),delta=(uint16_t)(r-state259.retired),used=(uint16_t)(a-r);
 if(a!=state259.sent||pending>4||delta>pending||used>4||!!(status259[2]&1)!=(used!=0)||!!(status259[2]&4)!=(used==4))return fail(3);
 state259.retired=r;return 1;
}
static unsigned drain(void){for(unsigned i=0;i<65536;i++){if(!status())return 0;if(state259.retired==state259.sent)return 1;}return fail(4);}
static unsigned phase(unsigned bit,unsigned error){
 for(unsigned i=0;i<256;i++){if(status259[7]&bit)return 1;if(!status())return 0;}return fail(error);
}
static unsigned send(unsigned n){
 if(n<16||n>256||u16(wire259+13)!=n-16||state259.error)return fail(5);
 for(unsigned i=0;(uint16_t)(state259.sent-state259.retired)>=4;i++)if(i==65536||!status())return fail(6);
 if(state259.sequence==65535)return fail(7);
 wire259[0]=0xe1;w16(wire259+3,state259.sequence);w32(wire259+5,state259.serial);w16(wire259+9,state259.generation);
 unsigned c=65535;for(unsigned i=0;i<=n;i++)c=crc16(c,wire259[i]);
 wire259[n+1]=c>>8;wire259[n+2]=c;
 if(!io259(wire259,n+3))return fail(1);
 state259.sent++;state259.sequence++;return 1;
}
/* The ABI remains259 so the same instruction/SPI harness can be reused. */
static unsigned batch_bytes260;
static unsigned flush260(void){
 if(!batch_bytes260)return !state259.error;
 w16(wire259+13,batch_bytes260-16);
 unsigned ok=send(batch_bytes260);batch_bytes260=0;return ok;
}
static unsigned map(unsigned at,const uint8_t *values,unsigned n){
 if((at|n)&1||!n||at+n>4096)return fail(8);
 if(!state259.token){
  if(!drain()||!phase(1,9)||(status259[7]&2))return fail(9);
  state259.token=u32(status259+8);
 }
 while(n){
  unsigned take=n>64?64:n;if(state259.token==0xffffffffu)return fail(10);
  if(batch_bytes260&&batch_bytes260+3+take>256&&!flush260())return 0;
  if(!batch_bytes260){
   for(unsigned i=1;i<=21;i++)wire259[i]=0;
   wire259[1]=14;wire259[2]=state259.bank;w32(wire259+17,state259.token);batch_bytes260=21;
  }
  unsigned p=1+batch_bytes260;w16(wire259+p,at);wire259[p+2]=take;
  for(unsigned i=0;i<take;i++)wire259[p+3+i]=values[i];
  wire259[21]++;batch_bytes260+=3+take;state259.token++;
  at+=take;n-=take;values+=take;
 }
 return 1;
}
static unsigned h2(const uint8_t *seal){
 if(!material259)return fail(19);
 const uint8_t *h=material259+5152;unsigned mask=u16(seal+34),raw=u16(seal+38),scroll=0,total=0;
 if((mask!=0x18&&mask!=0x1e)||raw>7)return fail(19);
 while(scroll<1121&&h[scroll]){if(h[scroll]>=128)return fail(19);total+=h[scroll];scroll+=5;}
 if(scroll>=1121||total!=224)return fail(19);scroll++;
 if(raw){
  unsigned at=0,lines=0,rawlines=0;
  while(at<81&&h[3169+at]){
   unsigned n=h[3169+at],mode=u16(h+3170+at);
   if(at+4>=81||n>=128||h[3250+at]!=n||h[3331+at]!=n||(mode!=0&&mode!=3)||u16(h+3251+at)!=mode)return fail(19);
   if(u16(h+3172+at)!=(mode?0x38:0x31)||u16(h+3253+at)!=(mode?0x58:0x51)||u16(h+3332+at)!=(mode?1:17)||u16(h+3334+at)!=(mode?0:mask==0x18?17:0))return fail(19);
   lines+=n;if(mode)rawlines+=n;at+=5;
  }
  if(at>=81||lines!=224||rawlines!=raw||h[3250+at]||h[3331+at])return fail(19);
  for(unsigned i=0;i<3;i++)if(u16(h+3412+i*2)!=at+1)return fail(19);
 }
 for(unsigned i=1;i<=48;i++)wire259[i]=0;
 wire259[1]=13;wire259[2]=5;w16(wire259+13,32);
 uint8_t *c=wire259+17;c[0]='H';c[1]='2';c[2]=2;c[3]=state259.bank;w32(c+4,1);w32(c+8,state259.serial);w16(c+12,state259.generation);w16(c+14,scroll);c[19]=mask;c[20]=raw;
 unsigned digest=65535;for(unsigned i=0;i<scroll;i++)digest=crc16(digest,h[i]);
 if(raw){
  for(unsigned i=0;i<3;i++)c[16+i]=u16(h+3412+i*2);
  unsigned block=65535;for(unsigned i=0;i<249;i++){
   block=crc16(block,h[3169+i]);if(i%16==15||i==248){digest=crc16(digest,block&255);digest=crc16(digest,block>>8);block=65535;}
  }
 }
 w16(c+22,digest);w16(c+24,scroll+(raw?249:0));w32(c+26,state259.serial>2?state259.serial-2:0);
 unsigned check=65535;for(unsigned i=0;i<30;i++)check=crc16(check,c[i]);w16(c+30,check);return send(48);
}
unsigned frame259(const uint8_t *plan,unsigned bytes,uint32_t serial,unsigned generation){
 if(!serial||serial==0xffffffffu||serial<=state259.serial)return fail(11);
 /* Caller owns immutable plan/material until return. Find the terminal SEAL
  * before publishing H2; no second certificate buffer or extra wire packet. */
 const uint8_t *seal262=0;unsigned scan262=0;
 while(scan262<bytes){
  if(bytes-scan262<2)return fail(12);unsigned n=u16(plan+scan262);scan262+=2;
  if(n<16||n>256||n>bytes-scan262)return fail(12);
  const uint8_t *p=plan+scan262;scan262+=n;
  if(n!=16+u16(p+12)||u32(p+4)!=serial||u16(p+8)!=generation)return fail(13);
  if(p[0]==3){if(n<40||scan262!=bytes)return fail(13);seal262=p;}
 }
 if(!seal262)return fail(18);
 if(!drain())return 0;
 state259.serial=serial;state259.generation=generation;state259.bank=(serial-1)&1;state259.sequence=0;state259.token=0;
 if(!h2(seal262))return 0;
 unsigned at=0,begin=0,seal=0;
 while(at<bytes){
  if(bytes-at<2)return fail(12);unsigned n=u16(plan+at);at+=2;
  if(n<16||n>256||n>bytes-at)return fail(12);const uint8_t *p=plan+at;at+=n;
  if(n!=16+u16(p+12)||u32(p+4)!=serial||u16(p+8)!=generation||seal)return fail(13);
  if(!begin&&p[0]!=1)return fail(14);if(p[0]==1){if(begin)return fail(14);begin=1;}
  if(p[0]==9&&p[1]==2){
   if(n<20||p[16]!=3)return fail(15);
   for(unsigned j=17;j<n;){
    if(n-j<3)return fail(15);unsigned off=u16(p+j),len=p[j+2]*2;j+=3;
    if(!len||len>64||len>n-j||!map(off,p+j,len))return fail(15);j+=len;
   }
   continue;
  }
  if(!flush260())return 0;
  if(p[0]>11||!p[0]||p[0]==9)return fail(16);
  if(p[0]==7){
   if(!drain()||!phase(2,17)||(status259[7]&4)||u16(status259+16)!=u16(p+14)||status259[18]!=((state259.bank<<2)|p[1])||u16(status259+19)!=u16(p+10)/(p[1]?32:16)||u16(status259+21)!=generation)return fail(17);
  }
  for(unsigned i=0;i<n;i++)wire259[i+1]=p[i];
  if(p[0]==7)w32(wire259+17,u32(status259+12));
  if(!send(n))return 0;
  if(p[0]==1||p[0]==7||p[0]==3){if(!drain())return 0;}
  if(p[0]==3)seal=1;
 }
 if(!begin||!seal)return fail(18);trace259(1,serial);return 1;
}
void reset259(void){
 batch_bytes260=0;
 state259.sent=state259.retired=state259.sequence=state259.generation=0;
 state259.serial=state259.token=0;state259.bank=state259.error=0;
}
