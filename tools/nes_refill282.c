/* SPDX-License-Identifier: MIT */
/* Two immutable plan banks; bounded supply before output SPI. No wait for an
 * occupied bank here: output traffic and fallback polling must still progress. */
#include <stdint.h>
extern int physical267(uint8_t *,unsigned);
extern unsigned progress282(const uint8_t *,unsigned);
extern unsigned plan_cache282,plan_flags282,plan_accepted282;
const uint8_t *plans267;
unsigned plan_bytes267,plan_at267,plan_sent267,plan_error267,plan_generation267;
static uint8_t wire267[248],reply267[20];
static unsigned crc8(const uint8_t *p,unsigned n){unsigned c=0;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c&128)?(c<<1)^7:c<<1;c&=255;}return c;}
static unsigned crc16(const uint8_t *p,unsigned n){unsigned c=65535;while(n--){c^=(unsigned)*p++<<8;for(unsigned i=0;i<8;i++)c=(c&32768)?(c<<1)^0x1021:c<<1;c&=65535;}return c;}
static int poll267(void){
 for(unsigned i=0;i<20;i++)reply267[i]=0;reply267[0]=0xe8;
 if(!physical267(reply267,20)||reply267[1]!=0xd7||reply267[2]!=4||reply267[18]||
    (reply267[3]&0xf8)||crc8(reply267+1,18)!=reply267[19])return 0;
 plan_flags282=reply267[3];plan_accepted282=256u*reply267[4]+reply267[5];plan_cache282=1;
 return 1;
}
int io259(uint8_t *p,unsigned n){
 if(plan_error267)return 0;
 for(unsigned supplied=0;supplied<2&&plan_at267<plan_bytes267;supplied++){
  if(!plan_cache282&&!poll267()){plan_error267=1;return 0;}
  if(plan_accepted282!=plan_sent267){plan_error267=2;return 0;}
  if(!(plan_flags282&1))break;
  const uint8_t *q=plans267+plan_at267;unsigned len=q[0]+256u*q[1],count=q[2];
  if(len<3||len>240||count<1||count>15||plan_at267+len+3>plan_bytes267){plan_error267=3;return 0;}
  wire267[0]=0xe9;wire267[1]=len;wire267[2]=len>>8;wire267[3]=count;
  for(unsigned i=0;i<len;i++)wire267[i+4]=q[i+3];
  unsigned c=crc16(q+3,len);wire267[len+4]=c>>8;wire267[len+5]=c;wire267[len+6]=crc8(wire267,len+6);wire267[len+7]=0xa5;
  if(!physical267(wire267,len+8)||!progress282(wire267,len+8)){plan_error267=4;return 0;}
  /* Response predates this seal. Re-query before another bank admission. */
  plan_cache282=0;plan_at267+=len+3;plan_sent267++;
 }
 unsigned command=p[0];
 if(!physical267(p,n))return 0;
 if(command==0xe1&&!progress282(p,n))return 0;
 /* E0/E2 do not carry plan progress. A busy bank can become free while
  * polling tile readiness, so the next service boundary must refresh E8. */
 if(command!=0xe1)plan_cache282=0;
 return 1;
}
unsigned finish267(void){
 if(plan_error267||plan_at267!=plan_bytes267)return 0;
 unsigned sent=0;
 for(unsigned i=0;i<65536;i++){
  if(!poll267())return 0;
  if(sent){if(plan_flags282==1&&plan_accepted282==0)return 1;}
  else if(plan_flags282==2&&plan_accepted282==plan_sent267){
   wire267[0]=0xea;wire267[1]=plan_generation267;wire267[2]=plan_generation267>>8;
   wire267[3]=plan_sent267>>8;wire267[4]=plan_sent267;wire267[5]=crc8(wire267,5);wire267[6]=0xa5;
   if(!physical267(wire267,7))return 0;sent=1;plan_cache282=0;
  }
 }
 return 0;
}
