/* SPDX-License-Identifier: MIT */
#include "nes_plan_service198.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct nes_native_sink165 sink;static struct nes_plan198 service;
static unsigned accepted,calls,bulks,plans,checks,used,head;static int bad=-1;
static uint8_t queue[16][12];static bool ended;static FILE *vectors;
static uint8_t crc8(const uint8_t *b,unsigned n){uint8_t c=0;while(n--){c^=*b++;for(unsigned i=0;i<8;i++)c=(uint8_t)(c&128?(c<<1)^7:c<<1);}return c;}
static uint16_t crc16(const uint8_t *b,unsigned n){uint16_t c=65535;while(n--){c^=(uint16_t)*b++<<8;for(unsigned i=0;i<8;i++)c=(uint16_t)(c&32768?(c<<1)^0x1021:c<<1);}return c;}
static bool guard(void *ctx){(void)ctx;return bad!=8;}
static bool exchange(void *ctx,const uint8_t *b,unsigned n,uint8_t ack[12]){
 (void)ctx;assert(used&&b[0]==7&&n==20&&!memcmp(b+16,queue[head]+8,4));bulks++;
 ack[0]=0;ack[1]=7;memcpy(ack+2,b+2,8);ack[10]=0x65;ack[11]=0x9a;
 if(bad==10)return false;
 used--;head++;return true;
}
static bool transfer(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 (void)ctx;calls++;if(bad==7)return false;
 if(tx[0]==0xe8){
  assert(n==20&&tx!=rx);memset(rx,0,n);rx[1]=0xd7;rx[2]=2;rx[3]=(uint8_t)((used||bad==9?0:1)|(ended?2:0));
  rx[4]=(uint8_t)(accepted>>8);rx[5]=(uint8_t)accepted;if(used)memcpy(rx+6,queue[head],12);
  switch(bad){case 0:rx[1]^=1;break;case 1:rx[2]=1;break;case 2:rx[18]=1;break;case 3:rx[3]|=128;break;
   case 4:rx[5]++;break;case 5:rx[6]=2;break;case 11:rx[7]=1;break;case 12:rx[3]|=2;break;}
  rx[19]=crc8(rx+1,18);if(bad==6)rx[19]^=1;
 }else{
  unsigned len=tx[1]+256u*tx[2],count=tx[3],at=4;
  assert(tx==rx&&tx[0]==0xe9&&n==len+8&&count>=1&&count<=16&&!used&&!ended&&tx[n-1]==0xa5&&crc8(tx,n-2)==tx[n-2]);
  assert(len<=512&&crc16(tx+4,len)==(unsigned)tx[len+4]*256+tx[len+5]);
  if(vectors){fprintf(vectors,"%03x",n);for(unsigned i=0;i<n;i++)fprintf(vectors," %02x",tx[i]);fprintf(vectors,"\n");}
  head=used=0;accepted++;
  for(unsigned q=0;q<count;q++){
   const uint8_t *b=tx+at;assert(at+16<=len+4&&b[15]==1);unsigned extra=0;
   for(unsigned i=0;i<8;i++)extra+=(b[1]>>i)&1;
   at+=16+extra*2;assert(at<=len+4);
   if(b[0]==3){assert(q==count-1);ended=true;continue;}
   uint8_t *d=queue[used++];memset(d,0,12);d[0]=1;d[1]=b[0]==1;plans++;
   unsigned unit=d[1]?32:16,offset=(b[4]+256u*b[5])*unit;
   d[2]=(uint8_t)unit;d[4]=(uint8_t)offset;d[5]=(uint8_t)(offset>>8);d[6]=b[2];d[7]=b[3];d[8]=(uint8_t)plans;d[9]=(uint8_t)(plans>>8);
  }
  assert(at==len+4);memset(rx,0xa7,n); // Prove no dependence on sent buffer after transfer.
 }
 return true;
}
static void init(unsigned generation){
 accepted=calls=bulks=used=head=0;ended=false;bad=-1;
 nes_sink165_reset(&sink,exchange,NULL);sink.state=NES_SINK165_BUILD;sink.generation=(uint16_t)generation;
 memset(&service,0,sizeof(service));service.transfer=transfer;service.guard=guard;service.sink=&sink;service.poll_limit=64;
}
static void zero(struct nes_plan191 *q){memset(q,0,sizeof(*q));for(unsigned i=0;i<8;i++)q->alt[i]=65535;}
static void unpack(struct nes_plan191 *q,const unsigned v[29]){
 zero(q);q->kind=(uint8_t)v[0];q->generation=(uint16_t)v[1];q->slot=(uint16_t)v[2];q->tag=(uint16_t)v[3];q->mask=(uint8_t)v[4];
 for(unsigned i=0;i<16;i++)q->row[i]=(uint8_t)v[5+i];
 for(unsigned i=0;i<8;i++)q->alt[i]=(uint16_t)v[21+i];
}
int main(int argc,char **argv){
 assert(argc==2);unsigned batches=0;struct nes_plan191 first;
 for(unsigned scene=0;scene<8;scene++){
  init(100+scene);char path[1024];snprintf(path,sizeof(path),"%s/scene%u.plans",argv[1],scene);FILE *f=fopen(path,"r");assert(f);
  snprintf(path,sizeof(path),"scene%u.batch",scene);vectors=fopen(path,"w");assert(vectors);unsigned v[29];
  while(fscanf(f,"%u",v)==1){
   for(unsigned i=1;i<29;i++)assert(fscanf(f,"%u",v+i)==1);
   struct nes_plan191 q;unpack(&q,v);if(scene==0&&q.kind==0&&q.slot==1)first=q;
   assert(nes_plan198_emit(&service,&q));
  }
  assert(nes_plan198_finish(&service)&&service.finished&&!used&&!sink.displayed&&accepted==service.sent);
  batches+=accepted;unsigned before=calls;assert(!nes_plan198_finish(&service)&&before==calls);
  fclose(f);fclose(vectors);vectors=NULL;checks++;
 }
 assert(plans==97&&batches==11);
 init(100);sink.bg_next=1;vectors=fopen("pressure.batch","w");assert(vectors);
 for(unsigned i=1;i<=512;i++){first.slot=(uint16_t)i;assert(nes_plan198_emit(&service,&first));}
  assert(nes_plan198_finish(&service)&&accepted==35&&bulks==512);fclose(vectors);vectors=NULL;checks++;
 // Maximum32B plans split at240B limit, then END. RX overwrites TX.
 init(100);sink.bg_next=1;for(unsigned i=0;i<8;i++)first.alt[i]=(uint16_t)i;
 for(unsigned i=1;i<=16;i++){first.slot=(uint16_t)i;assert(nes_plan198_emit(&service,&first));}
 assert(nes_plan198_finish(&service)&&accepted==3&&bulks==16);checks++;
 for(int mode=0;mode<13;mode++){
  init(123);struct nes_plan191 q;zero(&q);q.kind=2;q.generation=123;assert(nes_plan198_emit(&service,&q));
  bad=mode;assert(!nes_plan198_finish(&service)&&service.error);
  unsigned before=calls;assert(!nes_plan198_emit(&service,&q)&&calls==before);checks++;
 }
 init(123);struct nes_plan191 q;zero(&q);q.kind=2;q.generation=123;assert(nes_plan198_emit(&service,&q));sink.generation=124;
 assert(!nes_plan198_finish(&service)&&!calls);checks++;
 printf("PASS SERVICE198 scenes=8 plans=97 batches=11 pressure_batches=35 checks=%u size=%u\n",checks,(unsigned)sizeof(service));return 0;
}
