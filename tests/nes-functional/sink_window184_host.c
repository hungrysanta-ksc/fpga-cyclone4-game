/* SPDX-License-Identifier: MIT */
#include "nes_sink_window184.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct replay {FILE *f;unsigned calls,guards,fail_call,fail_guard,mode;};
static unsigned hex(const char *p){char b[3]={p[0],p[1],0};return (unsigned)strtoul(b,NULL,16);}
static bool transfer(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 struct replay *r=ctx;char a[519],b[519];unsigned size;
 assert(fscanf(r->f,"%u %518s %518s",&size,a,b)==3&&size==n);
 for(unsigned i=0;i<n;i++){assert(tx[i]==hex(a+i*2));rx[i]=(uint8_t)hex(b+i*2);}
 r->calls++;if(r->fail_call==r->calls)return false;
 if(r->mode&&n==20){
  if(r->mode==1)rx[1]=0xf6;
  if(r->mode==2)rx[2]|=0x80;
  if(r->mode==3)rx[4]++;
  if(r->mode==4)rx[6]++;
  if(r->mode==5)rx[19]^=1;
  if(r->mode!=5){unsigned c=0;for(unsigned i=1;i<19;i++){c^=rx[i];for(unsigned j=0;j<8;j++)c=((c<<1)^((c&128)?7:0))&255;}rx[19]=(uint8_t)c;}
 }
 return true;
}
static bool guard(void *ctx){struct replay *r=ctx;return ++r->guards!=r->fail_guard;}
static bool run(struct replay *r,unsigned wrap){
 struct nes_sink_window184 s;uint8_t ack[12],p[256];
 if(!nes_window184_init(&s,transfer,guard,r,32)){
  if(r->mode==2)assert(s.status_flags==128&&s.ack_status==0);
  if(r->mode==1||r->mode==5)assert(s.status_flags==0&&s.ack_status==0);
  return false;
 }
 if(wrap)s.sent=s.retired=0xfffc;
 for(unsigned i=0;i<33;i++){
  unsigned n=i==0?16:i==32?40:i%3==1?256:18;
  for(unsigned j=0;j<256;j++)p[j]=(uint8_t)(i*19+j*37);
  p[0]=i==0?1:i==32?3:i%3==1?2:i%3==2?4:5;p[1]=0;p[2]=(uint8_t)i;p[3]=0;
  p[4]=1;p[5]=p[6]=p[7]=0;p[8]=0x34;p[9]=0x12;p[10]=p[11]=0;
  p[12]=(uint8_t)(n-16);p[13]=0;p[14]=i%3==2?240:0;p[15]=(i!=0&&i!=32&&i%3==0)?2:0;
  bool ok=(i==0||i==32)?nes_window184_barrier(&s,p,n,ack):nes_window184_enqueue(&s,p,n);
  if(!ok){unsigned before=r->calls;assert(!nes_window184_enqueue(&s,p,n)&&r->calls==before);return false;}
 }
 assert(s.sent==(wrap?29:33)&&s.retired==s.sent&&ack[0]==1&&ack[1]==3&&ack[2]==32);
 assert(s.status_flags==2&&s.ack_status==1);
 unsigned extra;assert(fscanf(r->f,"%u",&extra)==EOF);return true;
}
int main(int argc,char **argv){
 assert(argc==3);unsigned wrap=(unsigned)atoi(argv[2]);struct replay r={0};r.f=fopen(argv[1],"r");assert(r.f);assert(run(&r,wrap));
 unsigned calls=r.calls,guards=r.guards;fclose(r.f);
 for(unsigned i=1;i<=calls;i++){r=(struct replay){.f=fopen(argv[1],"r"),.fail_call=i};assert(!run(&r,wrap));fclose(r.f);}
 for(unsigned i=1;i<=guards;i++){r=(struct replay){.f=fopen(argv[1],"r"),.fail_guard=i};assert(!run(&r,wrap));fclose(r.f);}
 for(unsigned i=1;i<=5;i++){r=(struct replay){.f=fopen(argv[1],"r"),.mode=i};assert(!run(&r,wrap));fclose(r.f);}
 printf("PASS WINDOW184 C calls=%u guards=%u failures=%u wrap=%u\n",calls,guards,calls+guards+5,wrap);return 0;
}
