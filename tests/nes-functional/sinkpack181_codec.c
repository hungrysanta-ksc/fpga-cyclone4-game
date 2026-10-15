/* SPDX-License-Identifier: MIT */
/* Encoder boundary check only. Real SNES ACK/PPU is tested separately. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "nes_native_sink165.c"
static const uint8_t *expected;
static unsigned length,checks;
static bool good_ack=true;
static unsigned word(const uint8_t *p){return p[0]|((unsigned)p[1]<<8);}
static bool exchange(void *ctx,const uint8_t *b,unsigned n,uint8_t ack[12]){
 (void)ctx;assert(n==16+word(b+12));assert(word(b+10)==17);
 bool repeated=length>=4 && !(length&1);
 for(unsigned i=2;i<length;i++)if(expected[i]!=expected[i&1])repeated=false;
 assert((b[0]==4)==repeated);
 if(repeated){assert(word(b+14)==length&&n==18);for(unsigned i=0;i<length;i++)assert(expected[i]==b[16+(i&1)]);}
 else {assert(b[0]==2&&word(b+14)==0&&n==length+16);assert(!memcmp(expected,b+16,length));}
 memset(ack,0,12);ack[1]=b[0];memcpy(ack+2,b+2,8);ack[10]=0x65;ack[11]=good_ack?0x9a:0;
 checks++;return true;
}
int main(void){
 struct nes_native_sink165 s;uint8_t data[240];
 for(unsigned n=1;n<=240;n++)for(unsigned mode=0;mode<4;mode++){
  for(unsigned i=0;i<n;i++)data[i]=(mode==0)?0:(uint8_t)(i&1?0x20:0x53);
  if(mode==2)data[n-1]^=1;
  if(mode==3)for(unsigned i=0;i<n;i++)data[i]=(uint8_t)(i*37+13);
  expected=data;length=n;good_ack=true;nes_sink165_reset(&s,exchange,NULL);s.state=NES_SINK165_BUILD;
  assert(packet(&s,2,2,17,data,n));assert(s.sequence==1&&s.state==NES_SINK165_BUILD);
 }
 expected=data;length=240;good_ack=false;nes_sink165_reset(&s,exchange,NULL);s.state=NES_SINK165_BUILD;
 assert(!packet(&s,2,2,17,data,240));assert(s.state==NES_SINK165_FAULT&&s.sequence==0);
 unsigned before=checks;assert(!packet(&s,2,2,17,data,240));assert(checks==before);
 printf("PASS sinkpack encoder %u exchanges, all lengths1..240,4patterns,badACK terminal\n",checks);return 0;
}
