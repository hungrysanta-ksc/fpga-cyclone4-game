/* SPDX-License-Identifier: MIT */
#include "nes_native_sink165.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
bool reference_build(const struct nes_native165 *,const uint16_t *,struct nes_native_video165 *,nes_native_video165_stage_fn,void *);
/* Host-only oracle and simulated tentative sink. No such arrays on MCU. */
static struct nes_native165 scene;
static struct nes_native_video165 gold,plan;
static struct nes_native_sink165 sink;
static uint8_t expected[2][16384],received[2][16384];
static uint16_t lut[64];
static unsigned oldcalls,calls,bytes,ordinal,fail_at,mode,oldtotal,newtotal,rejects,cases;
static unsigned le16(const uint8_t *b){return b[0]|((unsigned)b[1]<<8);}
static bool oldstage(void *ctx,unsigned kind,unsigned slot,const uint8_t *b,unsigned n){
 (void)ctx;assert(kind<2&&n==(kind?32u:16u));oldcalls++;
 memcpy(expected[kind]+slot*n,b,n);return true;
}
static bool exchange(void *ctx,const uint8_t *b,unsigned n,uint8_t ack[12]){
 (void)ctx;assert(n>=16&&n<=256&&sink.state==NES_SINK165_BUSY);ordinal++;
 if(ordinal==fail_at)return false;
 unsigned op=b[0],section=b[1],at=le16(b+10),size=le16(b+12);
 assert(n==size+16&&size<=240);
 if(op==2&&section<2){
  calls++;bytes+=size;assert(at+size<=(section?4096u:16384u));
  memcpy(received[section]+at,b+16,size);
  if(mode==0)assert(memcmp(expected[section]+at,b+16,size)==0);
 }else if(op==2){
  const uint8_t *p=section==2?gold.map:section==3?gold.cgram:section==4?gold.oam:gold.hdma;
  assert(section<=5&&memcmp(p+at,b+16,size)==0);
 }else assert(op==1||op==3);
 ack[0]=(uint8_t)(op==3);ack[1]=(uint8_t)op;memcpy(ack+2,b+2,8);ack[10]=0x65;ack[11]=0x9a;
 if(mode==2&&op==2)ack[2]^=1; /* stale ACK must not advance the batch */
 return true;
}
static void reset_sink(void){
 memset(received,0,sizeof(received));calls=bytes=ordinal=0;fail_at=0;mode=0;
 nes_sink165_reset(&sink,exchange,NULL);assert(nes_sink165_begin(&sink,scene.generation));
}
static void check(void){
 memset(expected,0,sizeof(expected));oldcalls=0;
 assert(reference_build(&scene,lut,&gold,oldstage,NULL));reset_sink();
 assert(nes_native_video165_build(&scene,lut,&plan,nes_sink165_pattern,&sink));
 assert(memcmp(&plan,&gold,sizeof(plan))==0);assert(memcmp(expected,received,sizeof(expected))==0);
 assert(calls==(plan.bg_count+14u)/15u+(plan.obj_count+6u)/7u);
 assert(oldcalls==plan.bg_count+plan.obj_count&&bytes==plan.bg_count*16u+plan.obj_count*32u);
 unsigned batches=calls;oldtotal+=oldcalls;newtotal+=calls;cases++;
 assert(nes_sink165_seal(&sink,&plan,5000)&&sink.displayed);
 printf("CASE generation=%u bg=%u obj=%u old=%u batch=%u payload=%u\n",scene.generation,plan.bg_count,plan.obj_count,oldcalls,batches,bytes);
 /* Every possible pattern-packet failure: invalid candidate, no SEAL/retry. */
 for(unsigned i=1;i<=batches;i++){
  reset_sink();fail_at=1+i;
  assert(!nes_native_video165_build(&scene,lut,&plan,nes_sink165_pattern,&sink));
  assert(!plan.valid&&plan.error==14&&sink.state==NES_SINK165_FAULT&&!sink.displayed&&ordinal==fail_at);
  assert(!nes_sink165_seal(&sink,&plan,5000)&&ordinal==fail_at);rejects++;
 }
 reset_sink();mode=2;
 assert(!nes_native_video165_build(&scene,lut,&plan,nes_sink165_pattern,&sink));
 assert(!plan.valid&&sink.bg_next==0&&sink.obj_next==0&&!sink.displayed);rejects++;
}
static void synthetic(unsigned bg,unsigned obj){
 memset(&scene,0,sizeof(scene));scene.state=NES_NATIVE165_COMMITTED;scene.generation=99;
 scene.counts[0]=33;scene.counts[1]=224;scene.counts[2]=(uint16_t)obj;scene.counts[4]=224;scene.counts[5]=32;
 for(unsigned x=0;x<33;x++)scene.maps[x]=(uint16_t)(x%bg);
 for(unsigned y=0;y<224;y++){scene.rows[y]=(uint8_t)(y&7);scene.raster[y]=(uint64_t)0x1e<<36;}
 scene.ntiles=(uint16_t)(bg+obj);
 for(unsigned i=0;i<bg+obj;i++){
  scene.tiles[i].tag=(uint16_t)(i<bg?i:200+i-bg);scene.tiles[i].kind=(uint8_t)(i<bg?1:2);
  for(unsigned j=0;j<16;j++)scene.tiles[i].data[j]=(uint8_t)(i*19+j);
 }
 for(unsigned i=0;i<obj;i++)scene.objects[i]=(200u+i)|((uint64_t)((i/8)*8)<<13)|((uint64_t)(i*2)<<22)|((uint64_t)255<<38)|((uint64_t)(i%8)<<46);
 check();
}
static void records(const char *path){
 memset(&scene,0,sizeof(scene));FILE *f=fopen(path,"r");assert(f);unsigned hi,mid,lo,token=0;
 const unsigned widths[]={2,1,7,4,7,1,2,8};
 while(fscanf(f,"%8x%8x%8x",&hi,&mid,&lo)==3){
  unsigned kind=hi>>29,gen=(hi>>13)&65535,index=hi&8191;uint64_t v=((uint64_t)mid<<32)|lo;
  uint8_t b[12]={(uint8_t)((kind<<5)|(index>>8)),(uint8_t)index,(uint8_t)(gen>>8),(uint8_t)gen};
  for(unsigned j=0;j<widths[kind];j++)b[4+j]=(uint8_t)(v>>((widths[kind]-1-j)*8));
  assert(nes_native165_packet(&scene,(uint16_t)token++,b,4+widths[kind]));
  if(scene.state==NES_NATIVE165_COMPLETE)scene.state=NES_NATIVE165_PREPARED;
 }
 fclose(f);check();
}
int main(int argc,char **argv){
 assert(argc==3);for(unsigned i=0;i<64;i++)lut[i]=(uint16_t)(i*73);
 for(unsigned i=0;i<7;i++)synthetic((unsigned[]){1,13,14,15,29,30,33}[i],(unsigned[]){0,1,6,7,8,14,128}[i]);
 records(argv[1]);records(argv[2]);
 uint8_t b[256]={0};
 const unsigned invalid[][4]={{0,0,0,0},{0,0,15,0},{0,0,256,0},{1,0,240,0},{2,0,16,0},{0,1023,32,1023},{1,127,64,127},{0,1,16,0}};
 for(unsigned i=0;i<sizeof(invalid)/sizeof(invalid[0]);i++){
  reset_sink();mode=1;sink.bg_next=sink.obj_next=(uint16_t)invalid[i][3];
  assert(!nes_sink165_pattern(&sink,invalid[i][0],invalid[i][1],b,invalid[i][2]));
  assert(sink.error==4&&ordinal==1);rejects++;
 }
 for(unsigned kind=0;kind<2;kind++){
  reset_sink();mode=1;unsigned limit=kind?128:1024,stride=kind?32:16;
  for(unsigned slot=0;slot<limit;){unsigned n=limit-slot,cap=240/stride;if(n>cap)n=cap;
   assert(nes_sink165_pattern(&sink,kind,slot,b,n*stride));slot+=n;}
  assert((kind?sink.obj_next:sink.bg_next)==limit);
 }
 printf("PASS BATCH174 cases=%u old_patterns=%u batches=%u rejects=%u context=%u plan=%u\n",cases,oldtotal,newtotal,rejects,(unsigned)sizeof(scene),(unsigned)sizeof(plan));
 return 0;
}
