/* SPDX-License-Identifier: MIT */
/* Actual ARM E8/E9 producer interleaved with E0/E1 on the same SPI bus.
 * Caller owns immutable encoded planner bytes; this is not the full RUN. */
#include <stdint.h>
extern int physical267(uint8_t *,unsigned);
const uint8_t *plans267;
unsigned plan_bytes267,plan_at267,plan_sent267,plan_error267,plan_generation267;
static uint8_t wire267[248],reply267[20];
static unsigned crc8(const uint8_t *p,unsigned n){unsigned c=0;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c&128)?(c<<1)^7:c<<1;c&=255;}return c;}
static unsigned crc16(const uint8_t *p,unsigned n){unsigned c=65535;while(n--){c^=(unsigned)*p++<<8;for(unsigned i=0;i<8;i++)c=(c&32768)?(c<<1)^0x1021:c<<1;c&=65535;}return c;}
static int poll267(void){
 for(unsigned i=0;i<20;i++)reply267[i]=0;reply267[0]=0xe8;
 if(!physical267(reply267,20)||reply267[1]!=0xd7||reply267[2]!=4||reply267[18]||
    (reply267[3]&0xf8)||crc8(reply267+1,18)!=reply267[19])return 0;
 return 1;
}
int io259(uint8_t *p,unsigned n){
 if(plan_error267)return 0;
 if(plan_at267<plan_bytes267){
  if(!poll267()){plan_error267=1;return 0;}
  if(((unsigned)reply267[4]*256+reply267[5])!=plan_sent267){plan_error267=2;return 0;}
  if(reply267[3]&1){
   const uint8_t *q=plans267+plan_at267;unsigned len=q[0]+256u*q[1],count=q[2];
   if(len<3||len>240||count<1||count>15||plan_at267+len+3>plan_bytes267){plan_error267=3;return 0;}
   wire267[0]=0xe9;wire267[1]=len;wire267[2]=len>>8;wire267[3]=count;
   for(unsigned i=0;i<len;i++)wire267[i+4]=q[i+3];
   unsigned c=crc16(q+3,len);wire267[len+4]=c>>8;wire267[len+5]=c;wire267[len+6]=crc8(wire267,len+6);wire267[len+7]=0xa5;
   if(!physical267(wire267,len+8)){plan_error267=4;return 0;}
   plan_at267+=len+3;plan_sent267++;
  }
 }
 return physical267(p,n);
}
unsigned finish267(void){
 if(plan_error267||plan_at267!=plan_bytes267)return 0;
 unsigned sent=0;
 for(unsigned i=0;i<65536;i++){
  if(!poll267())return 0;
  unsigned accepted=256u*reply267[4]+reply267[5];
  if(sent){if(reply267[3]==1&&accepted==0)return 1;}
  else if(reply267[3]==2&&accepted==plan_sent267){
   wire267[0]=0xea;wire267[1]=plan_generation267;wire267[2]=plan_generation267>>8;
   wire267[3]=plan_sent267>>8;wire267[4]=plan_sent267;wire267[5]=crc8(wire267,5);wire267[6]=0xa5;
   if(!physical267(wire267,7))return 0;sent=1;
  }
 }
 return 0;
}
