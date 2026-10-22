/* SPDX-License-Identifier: MIT */
/* Diagnostic D0/D1/D2/D3 transport on the same ARM SPI callback. The expected
 * digest is an independent replay oracle, NOT a production N5 decoder. */
#include <stdint.h>
extern int io259(uint8_t *,unsigned);
static unsigned crc(unsigned c,unsigned b,unsigned bits){
 c^=b<<(bits-8);for(unsigned i=0;i<8;i++)c=(c&(1u<<(bits-1)))?(c<<1)^(bits==8?7:0x1021):c<<1;
 return c&((1u<<bits)-1);
}
static int control(uint8_t b[259],unsigned op,unsigned offset,unsigned arg){
 b[0]=op;b[1]=offset>>16;b[2]=offset>>8;b[3]=offset;b[4]=arg;b[5]=~arg;
 unsigned c=0;for(unsigned i=0;i<6;i++)c=crc(c,b[i],8);b[6]=c;b[7]=0xa5;
 if(!io259(b,8))return 0;c=0;for(unsigned i=1;i<7;i++)c=crc(c,b[i],8);
 return b[1]==0xd8&&!(b[2]&0xfc)&&b[7]==c;
}
unsigned read_source259(unsigned total,unsigned gen,unsigned token,uint32_t expected){
 uint8_t b[259];unsigned consumed=0;uint32_t hash=2166136261u;
 while(consumed<total){
  unsigned poll;
  for(poll=0;poll<65536;poll++){if(!control(b,0xd0,0,0))return 0;if(b[2]&1)break;}
  if(poll==65536||((unsigned)b[3]<<8|b[4])!=token||b[5]||!b[6]||b[6]>248)return 0;
  unsigned n=b[6];if(n>total-consumed)return 0;
  for(unsigned i=0;i<n+3;i++)b[i]=0;b[0]=0xd1;
  if(!io259(b,n+3))return 0;
  unsigned c=65535;for(unsigned i=1;i<=n;i++){c=crc(c,b[i],16);hash=(hash^b[i])*16777619u;}
  if(c!=((unsigned)b[n+1]<<8|b[n+2])||token==65535||!control(b,0xd2,token,0))return 0;
  token++;consumed+=n;
 }
 if(hash!=expected||gen>65535||!control(b,0xd3,gen,1))return 0;
 return token;
}
