/* SPDX-License-Identifier: MIT */
#include "nes_resident211.h"
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
void baseline_reset(struct nes_resident211 *);
bool baseline_begin(struct nes_resident211 *,uint32_t,bool,uint16_t,nes_resident211_write_fn,void *);
unsigned baseline_slot(struct nes_resident211 *,struct nes_native_video165 *,uint64_t,struct nes_plan191 *);
bool baseline_prepare(struct nes_resident211 *,uint64_t);
bool baseline_commit(struct nes_resident211 *,uint32_t,uint16_t,unsigned,bool);
void baseline_abort(struct nes_resident211 *);
unsigned long long baseline_probes,index221_probes,index221_rebuild;
static struct nes_resident211 state[2];
static struct nes_native_video165 video[2];
static struct nes_plan191 last[2];
static unsigned writes[2],mode,fail_after,requests,frames,errors;
static bool writer(void *ctx,unsigned bank,const struct nes_plan191 *q){
 (void)ctx;assert(bank==state[mode].target);
 assert(!state[mode].displayed||bank!=state[mode].active);
 last[mode]=*q;writes[mode]++;
 return !fail_after||writes[mode]<fail_after;
}
static void equal(void){
 assert(!memcmp(&state[0],&state[1],offsetof(struct nes_resident211,index_head)));
 assert(!memcmp(&video[0],&video[1],sizeof video[0]));
 assert(writes[0]==writes[1]&&!memcmp(&last[0],&last[1],sizeof last[0]));
}
static void reset(void){
 baseline_reset(&state[0]);nes_resident211_reset(&state[1]);
 memset(video,0,sizeof video);memset(last,0,sizeof last);memset(writes,0,sizeof writes);
 fail_after=0;equal();
}
static void begin(unsigned epoch,unsigned generation){
 memset(video,0,sizeof video);
 mode=0;bool a=baseline_begin(&state[0],epoch,true,(uint16_t)generation,writer,NULL);
 mode=1;bool b=nes_resident211_begin(&state[1],epoch,true,(uint16_t)generation,writer,NULL);
 assert(a==b&&a);equal();frames++;
}
static unsigned slot(unsigned kind,unsigned tag,unsigned mask,uint64_t key,unsigned transform){
 struct nes_plan191 q[2];memset(q,0,sizeof q);
 q[0].generation=state[0].generation;q[0].kind=(uint8_t)kind;q[0].tag=(uint16_t)tag;q[0].mask=(uint8_t)mask;
 for(unsigned j=0;j<8;j++){q[0].alt[j]=UINT16_MAX;q[0].row[2*j]=q[0].row[2*j+1]=(uint8_t)j;}
 if(transform){q[0].row[0]=3;q[0].alt[7]=(uint16_t)((tag+1)&8191);}
 q[1]=q[0];mode=0;unsigned a=baseline_slot(&state[0],&video[0],key,&q[0]);
 mode=1;unsigned b=nes_resident211_slot(&state[1],&video[1],key,&q[1]);
 assert(a==b&&!memcmp(&q[0],&q[1],sizeof q[0]));equal();requests++;return a;
}
static void end(unsigned bad){
 uint64_t dirty=UINT64_C(1)<<(frames%64);
 assert(baseline_prepare(&state[0],dirty)==nes_resident211_prepare(&state[1],dirty));equal();
 bool a=baseline_commit(&state[0],state[0].serial+(bad==1),state[0].generation+(bad==2),state[0].target,bad!=3);
 bool b=nes_resident211_commit(&state[1],state[1].serial+(bad==1),state[1].generation+(bad==2),state[1].target,bad!=3);
 assert(a==b&&a==!bad);equal();
}
static unsigned hash_key(uint64_t key){
 uint32_t h=(uint32_t)key^(uint32_t)(key>>32);h^=h>>16;h*=UINT32_C(0x45d9f3b);h^=h>>16;return(h^0xb7)&255;
}
int main(void){
 reset();
 /* Synthetic scrolling identities, repeated cells, eviction, epoch changes,
  * altered rows/alt sources and masked objects; exact old slot/wire sequence. */
 for(unsigned f=0;f<180;f++){
  begin(1+f/53,(65500+f)&65535);assert(slot(2,0,0,0,0)==0);
  for(unsigned pass=0;pass<3;pass++)for(unsigned i=0;i<384;i++){
   unsigned tag=(i*13+(f/4)*17)&8191,shape=i%19==0;
   uint64_t key=tag|(shape?(UINT64_C(1)<<63):0);
   assert(slot(0,tag,255,key,shape)<1024);
  }
  for(unsigned i=0;i<96;i++){
   unsigned tag=(i*31+f)&8191,mask=(i%7)+1;
   uint64_t key=tag|((uint64_t)mask<<13);
   assert(slot(1,tag,mask,key,0)<128);assert(slot(1,tag,mask,key,0)<128);
  }
  end(0);
 }
 assert(baseline_probes<=UINT32_MAX&&index221_probes<=UINT32_MAX&&index221_rebuild<=UINT32_MAX);
 printf("WORKLOAD frames=180 requests=%u baseline_probes=%lu indexed_probes=%lu rebuild_visits=%lu synthetic_not_fps=1\n",
        requests,(unsigned long)baseline_probes,(unsigned long)index221_probes,(unsigned long)index221_rebuild);
 assert(index221_probes+index221_rebuild<baseline_probes);
 /* Deliberate same bucket keys must never alias; include64-bit differences. */
 reset();begin(9,7);slot(2,0,0,0,0);
 unsigned found=0;
 for(uint64_t key=1;found<256;key++)if(hash_key(key)==0){
  assert(slot(0,found,255,key,0)<1024);assert(slot(0,found,255,key,0)<1024);found++;
 }
 end(0);
 reset();begin(9,8);slot(2,0,0,0,0);
 for(unsigned i=1;i<1024;i++)assert(slot(0,i,255,UINT64_C(0x1234567800000000)|i,0)==i);
 assert(slot(0,1024,255,1024,0)==UINT16_MAX);errors++;
 for(unsigned bad=1;bad<=3;bad++){reset();begin(1,bad);slot(2,0,0,0,0);end(bad);errors++;}
 reset();begin(1,1);fail_after=3;slot(2,0,0,0,0);slot(0,4,255,4,0);
 assert(slot(0,8,255,8,0)==UINT16_MAX);errors++;
 baseline_abort(&state[0]);nes_resident211_abort(&state[1]);equal();
 reset();begin(42,0);slot(2,0,0,0,0);end(0);
 printf("PASS INDEX221 requests=%u frames=%u fault_cases=%u state_host_bytes=%u extra_index_bytes=%u exact_slots_and_plans=1\n",
        requests,frames,errors,(unsigned)sizeof state[0],(unsigned)(sizeof state[0].index_head+sizeof state[0].index_next));
 return 0;
}
