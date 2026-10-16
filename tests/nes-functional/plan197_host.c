/* SPDX-License-Identifier: MIT */
#include "nes_plan_service197.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct nes_native_sink165 sink;static struct nes_plan197 service;
static unsigned accepted,calls,bulks,plans,checks;static int bad=-1;
static uint8_t descriptor[12];static bool pending,ended;static FILE *vectors;
static uint8_t crc8(const uint8_t *b,unsigned n){uint8_t c=0;while(n--){c^=*b++;for(unsigned i=0;i<8;i++)c=(uint8_t)(c&128?(c<<1)^7:c<<1);}return c;}
static uint16_t crc16(const uint8_t *b,unsigned n){uint16_t c=65535;while(n--){c^=(uint16_t)*b++<<8;for(unsigned i=0;i<8;i++)c=(uint16_t)(c&32768?(c<<1)^0x1021:c<<1);}return c;}
static bool guard(void *ctx){(void)ctx;return bad!=8;}
static bool exchange(void *ctx,const uint8_t *b,unsigned n,uint8_t ack[12]){
 (void)ctx;assert(pending&&b[0]==7&&n==20&&!memcmp(b+16,descriptor+8,4));bulks++;
 ack[0]=0;ack[1]=7;memcpy(ack+2,b+2,8);ack[10]=0x65;ack[11]=0x9a;
 if(bad==10)return false;
 pending=false;return true;
}
static bool transfer(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 (void)ctx;calls++;memset(rx,0,n);if(bad==7)return false;
 if(tx[0]==0xe8){
  assert(n==20);rx[1]=0xd7;rx[2]=1;rx[3]=(uint8_t)((pending||bad==9?0:1)|(ended?2:0));
  rx[4]=(uint8_t)(accepted>>8);rx[5]=(uint8_t)accepted;
  if(pending)memcpy(rx+6,descriptor,12);
  switch(bad){case 0:rx[1]^=1;break;case 1:rx[2]=2;break;case 2:rx[18]=1;break;
   case 3:rx[3]|=128;break;case 4:rx[5]++;break;case 5:rx[6]=2;break;case 11:rx[7]=1;break;case 12:rx[3]|=2;break;}
  rx[19]=crc8(rx+1,18);if(bad==6)rx[19]^=1;
 }else{
  assert(tx[0]==0xe9&&n==tx[1]+6u&&!pending&&!ended&&tx[n-1]==0xa5&&crc8(tx,n-2)==tx[n-2]);
  unsigned len=tx[1];const uint8_t *b=tx+2;assert(len>=16&&len<=32&&b[15]==1&&crc16(b,len)==(unsigned)tx[len+2]*256+tx[len+3]);
  if(vectors){fprintf(vectors,"%02x",n);for(unsigned i=0;i<n;i++)fprintf(vectors," %02x",tx[i]);fprintf(vectors,"\n");}
  accepted++;
  if(b[0]==3){ended=true;return true;}
  plans++;pending=true;memset(descriptor,0,12);descriptor[0]=1;descriptor[1]=b[0]==1;
  unsigned unit=descriptor[1]?32:16,slot=b[4]+256u*b[5],offset=slot*unit;
  descriptor[2]=(uint8_t)unit;descriptor[4]=(uint8_t)offset;descriptor[5]=(uint8_t)(offset>>8);
  descriptor[6]=b[2];descriptor[7]=b[3];descriptor[8]=(uint8_t)accepted;descriptor[9]=(uint8_t)(accepted>>8);
 }
 return true;
}
static void init(unsigned generation){
 accepted=calls=bulks=0;pending=ended=false;bad=-1;
 nes_sink165_reset(&sink,exchange,NULL);sink.state=NES_SINK165_BUILD;sink.generation=(uint16_t)generation;
 memset(&service,0,sizeof(service));service.transfer=transfer;service.guard=guard;service.sink=&sink;service.poll_limit=8;
}
static void zero(struct nes_plan191 *q){memset(q,0,sizeof(*q));for(unsigned i=0;i<8;i++)q->alt[i]=65535;}
int main(int argc,char **argv){
 assert(argc==2);unsigned total_bulk=0;
 for(unsigned scene=0;scene<8;scene++){
  init(100+scene);char path[1024];snprintf(path,sizeof(path),"%s/scene%u.plans",argv[1],scene);FILE *f=fopen(path,"r");assert(f);
  snprintf(path,sizeof(path),"scene%u.requests",scene);vectors=fopen(path,"w");assert(vectors);unsigned v[29];
  while(fscanf(f,"%u",v)==1){
   for(unsigned i=1;i<29;i++)assert(fscanf(f,"%u",v+i)==1);
   struct nes_plan191 q;zero(&q);q.kind=(uint8_t)v[0];q.generation=(uint16_t)v[1];q.slot=(uint16_t)v[2];q.tag=(uint16_t)v[3];q.mask=(uint8_t)v[4];
   for(unsigned i=0;i<16;i++)q.row[i]=(uint8_t)v[5+i];
   for(unsigned i=0;i<8;i++)q.alt[i]=(uint16_t)v[21+i];
   assert(nes_plan197_emit(&service,&q));
  }
  assert(nes_plan197_finish(&service)&&service.finished&&!pending&&!sink.displayed&&accepted==service.sent);
  unsigned before=calls;assert(!nes_plan197_finish(&service)&&before==calls);total_bulk+=bulks;
  fclose(f);fclose(vectors);vectors=NULL;checks++;
 }
 assert(plans==97&&total_bulk==97);
 for(int mode=0;mode<13;mode++){
  init(123);struct nes_plan191 q;zero(&q);q.kind=2;q.generation=123;
  if(mode==10)assert(nes_plan197_emit(&service,&q));
  bad=mode;assert(!nes_plan197_emit(&service,&q)&&service.error);
  unsigned before=calls;assert(!nes_plan197_emit(&service,&q)&&calls==before);checks++;
 }
 printf("PASS SERVICE197 plans=97 drained=97 checks=%u\n",checks);return 0;
}
