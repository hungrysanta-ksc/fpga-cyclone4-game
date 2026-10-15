/* SPDX-License-Identifier: MIT */
/* Independent decoded bytes/observed wire cost; ACK here is deliberately mock. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "nes_native_sink165.c"
static const uint8_t *expected;
static unsigned length,at,cost,calls,total,fail_at;
static bool transport_fail;
static unsigned word(const uint8_t *p){return p[0]|((unsigned)p[1]<<8);}
static bool exchange(void *ctx,const uint8_t *b,unsigned n,uint8_t ack[12]){
 (void)ctx;calls++;total++;
 assert(n==16+word(b+12)&&b[1]==2&&word(b+10)==17+at);
 assert(word(b+2)==calls-1);
 unsigned count=word(b+12);
 if(b[0]==4||b[0]==5){
  assert(n==18);count=word(b+14);
  assert(!(count&1));assert(b[0]==4?(count>=4&&count<=240):(count>=242&&count<=4096));
 }else assert(b[0]==2&&!word(b+14)&&count<=240);
 assert(count&&at+count<=length);
 for(unsigned i=0;i<count;i++)assert(b[16+(b[0]>=4?(i&1):i)]==expected[at+i]);
 cost+=8*(n+35)+63;at+=count;
 memset(ack,0,12);ack[1]=b[0];memcpy(ack+2,b+2,8);ack[10]=0x65;ack[11]=0x9a;
 if(calls==fail_at){if(transport_fail)return false;ack[11]^=1;}
 return true;
}
static unsigned baseline(const uint8_t *b,unsigned n){
 unsigned cost=0;
 for(unsigned p=0;p<n;){
  unsigned k=n-p;if(k>240)k=240;
  bool same=k>=4&&!(k&1);
  for(unsigned j=2;j<k;j++)if(b[p+j]!=b[p+(j&1)])same=false;
  cost+=8*(16+(same?2:k)+35)+63;p+=k;
 }
 return cost;
}
int main(void){
 struct nes_native_sink165 s;uint8_t b[4097];unsigned cases=0;
 for(unsigned n=1;n<=4096;n++)for(unsigned mode=0;mode<5;mode++){
  for(unsigned i=0;i<n;i++){
   b[i]=(uint8_t)(i*37+13);
   if(mode==0)b[i]=0;
   if(mode==1)b[i]=(uint8_t)(i&1?0x53:0x20);
   if(mode==2&&i>=13&&i<n-7)b[i]=0x55;
   if(mode==3&&((i/70)%2))b[i]=(uint8_t)(i&1?0x42:0x81);
  }
  expected=b;length=n;at=cost=calls=fail_at=0;
  nes_sink165_reset(&s,exchange,NULL);s.state=NES_SINK165_BUILD;
  assert(span(&s,2,17,b,n));assert(at==n&&cost<=baseline(b,n));
  assert(s.sequence==calls&&s.state==NES_SINK165_BUILD);cases++;
 }
 for(unsigned i=0;i<800;i++)b[i]=(uint8_t)(i*37+13);
 for(unsigned failure=1;failure<=4;failure++)for(unsigned io=0;io<2;io++){
  nes_sink165_reset(&s,exchange,NULL);s.state=NES_SINK165_BUILD;
  expected=b;length=800;at=cost=calls=0;fail_at=failure;transport_fail=io!=0;
  assert(!span(&s,2,17,b,800));assert(calls==failure&&s.sequence==failure-1&&s.state==NES_SINK165_FAULT);
  assert(!span(&s,2,17,b,800));assert(calls==failure);cases++;
 }
 for(unsigned mode=0;mode<3;mode++){
  nes_sink165_reset(&s,exchange,NULL);s.state=NES_SINK165_BUILD;calls=fail_at=0;
  assert(!span(&s,2,17,mode==2?NULL:b,mode==0?0:4097));assert(!calls);cases++;
 }
 printf("PASS stream181 %u cases %u mock exchanges; exact bytes, non-increasing wire cost, terminal ACK/IO failures\n",cases,total);
 return 0;
}
