/* SPDX-License-Identifier: MIT */
#include <stdint.h>
#include "nes_crc283.h"
extern int physical267(uint8_t *,unsigned);
extern unsigned progress282(const uint8_t *,unsigned);
extern unsigned plan_cache282,plan_flags282,plan_accepted282;
extern void wait284(void);
extern void irq_begin284(void),irq_end284(void);
const uint8_t *plans267;
unsigned plan_bytes267,plan_at267,plan_sent267,plan_error267,plan_generation267;
unsigned wait_armed284;
static uint8_t wire267[248],reply267[12];
static unsigned crc8(const uint8_t *p,unsigned n){unsigned c=0;while(n--)c=crc_byte283(c,*p++);return c;}
static unsigned crc16(const uint8_t *p,unsigned n){unsigned c=65535;while(n--){c^=(unsigned)*p++<<8;for(unsigned i=0;i<8;i++)c=(c&32768)?(c<<1)^0x1021:c<<1;c&=65535;}return c;}
static int poll267(void){
 if(wait_armed284)wait284();
 for(unsigned i=0;i<12;i++)reply267[i]=0;reply267[0]=0xe2;
 if(!physical267(reply267,12)||!progress282(reply267,12))return 0;
 irq_begin284();wait_armed284=1;return 1;
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
  plan_cache282=0;wait_armed284=0;plan_at267+=len+3;plan_sent267++;
 }
 unsigned command=p[0];
 if(command==0xe2&&wait_armed284)wait284();
 if(!physical267(p,n))return 0;
 if((command==0xe1||command==0xe2)&&!progress282(p,n))return 0;
 wait_armed284=command==0xe2;
 /* A busy plan bank stays cached until checked autonomous progress arrives.
  * E0 disarms the hardware snapshot; invalidate its plan view conservatively. */
 if(command==0xe0)plan_cache282=0;
 return 1;
}
static unsigned finish_core284(void){
 if(plan_error267||plan_at267!=plan_bytes267)return 0;
 unsigned sent=0;
 for(unsigned i=0;i<65536;i++){
  if(!plan_cache282&&!poll267())return 0;
  if(sent){if(plan_flags282==1&&plan_accepted282==0)return 1;}
  else if(plan_flags282==2&&plan_accepted282==plan_sent267){
   wire267[0]=0xea;wire267[1]=plan_generation267;wire267[2]=plan_generation267>>8;
   wire267[3]=plan_sent267>>8;wire267[4]=plan_sent267;wire267[5]=crc8(wire267,5);wire267[6]=0xa5;
   if(!physical267(wire267,7))return 0;sent=1;plan_cache282=0;wait_armed284=0;continue;
  }
  if(!poll267())return 0;
 }
 return 0;
}
unsigned finish267(void){unsigned ok=finish_core284();irq_end284();return ok;}
