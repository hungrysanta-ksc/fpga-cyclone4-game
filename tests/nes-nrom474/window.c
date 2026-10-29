/* SPDX-License-Identifier: MIT */
#include "nes_sink_window184.h"
#include "nes_cost471.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static uint32_t counter;static unsigned counter_on,guards,guard_fail;
uint32_t nes_cost474_test_now(void){uint32_t v=counter;if(counter_on)counter+=84*8;return v;}
static bool timer_guard(void *ctx){(void)ctx;return ++guards!=guard_fail;}
struct model {unsigned us,ready,polls,sent,retired,max_used,quiet,reason[3],stop,corrupt;uint8_t last[10];};
static uint8_t crc8(uint8_t c,uint8_t b){c^=b;for(unsigned i=0;i<8;i++)c=(uint8_t)(c&128?(c<<1)^7:c<<1);return c;}
static bool guard(void *ctx){struct model *m=ctx;return !m->stop||m->us<m->stop;}
static bool pause_model(void *ctx,bool (*g)(void *),unsigned reason,bool progress){
 struct model *m=ctx;assert(reason<3);m->reason[reason]++;
 if(progress)return true;
 m->quiet++;
 for(unsigned i=0;i<16;i++){m->us+=8;if(!g(ctx))return false;}
 return true;
}
static bool transfer(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 struct model *m=ctx;assert(guard(ctx));unsigned op=tx[0];
 if(op==0xe1){
  assert(n==19);memcpy(m->last,tx+1,10);m->sent++;m->us+=70;
  unsigned used=m->sent-m->retired;assert(used<=4);if(used>m->max_used)m->max_used=used;
  memset(rx,0,n);return true;
 }
 assert(op==0xe0&&n==20);m->polls++;m->us+=110;
 if(m->us>=m->ready)m->retired=m->sent;
 memset(rx,0,n);rx[1]=0xf7;unsigned used=m->sent-m->retired;
 rx[2]=(uint8_t)((used?1:0)|(used==4?4:0)|(m->retired?2:0));
 rx[3]=(uint8_t)(m->sent>>8);rx[4]=(uint8_t)m->sent;rx[5]=(uint8_t)(m->retired>>8);rx[6]=(uint8_t)m->retired;
 if(m->retired){rx[7]=m->last[0]==3;rx[8]=m->last[0];memcpy(rx+9,m->last+2,8);rx[18]=0x9a;rx[17]=0x65;}
 if(m->corrupt==2)rx[10]^=1;
 for(unsigned i=1;i<19;i++)rx[19]=crc8(rx[19],rx[i]);
 if(m->corrupt==1)rx[19]^=1;
 return true;
}
static void packet(uint8_t p[16],unsigned op,unsigned sequence){
 memset(p,0,16);p[0]=(uint8_t)op;p[2]=(uint8_t)sequence;p[4]=7;p[8]=1;
}
static struct model drain(bool paced){
 struct model m={0};m.ready=2000;struct nes_sink_window184 s;uint8_t p[16],ack[12];
 assert(nes_window184_init(&s,transfer,guard,&m,1000));if(paced)s.wait=pause_model;
 packet(p,2,0);assert(nes_window184_enqueue(&s,p,16));assert(s.sent==1&&s.retired==0);
 assert(nes_window184_drain(&s,ack));assert(s.sent==s.retired&&m.us>=m.ready&&ack[0]==0);
 return m;
}
int main(void){
 struct model old=drain(false),now=drain(true);
 assert(now.polls<old.polls&&now.us<=old.us+238&&now.reason[1]&&now.quiet);
 struct model m={0};m.ready=2000;struct nes_sink_window184 s;uint8_t p[16],ack[12];
 assert(nes_window184_init(&s,transfer,guard,&m,1000));s.wait=pause_model;
 for(unsigned i=0;i<5;i++){packet(p,2,i);assert(nes_window184_enqueue(&s,p,16));}
 assert(m.max_used==4&&m.reason[0]);assert(nes_window184_drain(&s,ack));
 packet(p,3,5);assert(nes_window184_barrier(&s,p,16,ack)&&ack[0]==1&&m.reason[2]);
 memset(&m,0,sizeof m);m.ready=2000;m.stop=500;
 assert(nes_window184_init(&s,transfer,guard,&m,1000));s.wait=pause_model;packet(p,2,0);
 assert(nes_window184_enqueue(&s,p,16));assert(!nes_window184_drain(&s,ack)&&s.error==2);
 unsigned polls=m.polls;assert(!nes_window184_drain(&s,ack)&&m.polls==polls);
 for(unsigned bad=1;bad<=2;bad++){
  memset(&m,0,sizeof m);assert(nes_window184_init(&s,transfer,guard,&m,1000));s.wait=pause_model;
  packet(p,3,0);m.corrupt=bad;assert(!nes_window184_barrier(&s,p,16,ack));assert(s.error==(bad==1?4:8));
 }
 counter_on=1;nes_cost471_begin();assert(nes_cost471_available);guards=guard_fail=0;
 counter=0xffffff00u;assert(nes_cost474_pause(NULL,timer_guard,2,false));
 assert(guards>=16&&guards<=18&&nes_cost474_waits[2].cycles>=84*128);
 guards=0;guard_fail=3;assert(!nes_cost474_pause(NULL,timer_guard,1,false)&&guards==3);
 unsigned before=guards;assert(nes_cost474_pause(NULL,timer_guard,0,true)&&guards==before);
 nes_cost471_available=0;guard_fail=0;assert(nes_cost474_pause(NULL,timer_guard,0,false)&&guards==before+1);
 nes_cost471_end();printf("PASS474 window old_polls=%u quiet_polls=%u old_us=%u quiet_us=%u credit4/ACK/CRC/STOP/DWTwrap/fallback\n",old.polls,now.polls,old.us,now.us);
 return 0;
}
