/* SPDX-License-Identifier: MIT */
#include "nes_sink_window184.h"
#include <string.h>
static bool fail(struct nes_sink_window184 *s,unsigned e){if(s&&!s->error)s->error=(uint8_t)e;return false;}
static uint8_t crc8(uint8_t c,uint8_t b){c^=b;for(unsigned i=0;i<8;i++)c=(uint8_t)(c&128?(c<<1)^7:c<<1);return c;}
static uint16_t crc16(uint16_t c,uint8_t b){c^=(uint16_t)b<<8;for(unsigned i=0;i<8;i++)c=(uint16_t)(c&0x8000?(c<<1)^0x1021:c<<1);return c;}
static bool io(struct nes_sink_window184 *s,const uint8_t *tx,uint8_t *rx,unsigned n){
 if(s->error)return false;
 if(!s->guard(s->ctx))return fail(s,2);
 if(!s->transfer(s->ctx,tx,rx,n))return fail(s,3);
 return true;
}
static bool status(struct nes_sink_window184 *s,uint8_t ack[12]){
 uint8_t tx[20]={0xe0},rx[20];if(!io(s,tx,rx,20))return false;
 uint8_t c=0;for(unsigned i=1;i<19;i++)c=crc8(c,rx[i]);
 if(rx[1]!=0xf7||rx[19]!=c)return fail(s,4);
 s->status_flags=rx[2];s->ack_status=(rx[2]&2)?rx[7]:0;
 if(rx[2]&0xf8)return fail(s,4);
 uint16_t a=(uint16_t)((rx[3]<<8)|rx[4]),r=(uint16_t)((rx[5]<<8)|rx[6]);
 unsigned pending=(uint16_t)(s->sent-s->retired),delta=(uint16_t)(r-s->retired),used=(uint16_t)(a-r);
 if(a!=s->sent||pending>4||delta>pending||used>4||!!(rx[2]&1)!=(used!=0)||!!(rx[2]&4)!=(used==4))return fail(s,5);
 if(!s->ever_sent){if(rx[2]||a||r)return fail(s,6);}
 else if(r==s->sent && !(rx[2]&2))return fail(s,6);
 s->retired=r;memcpy(ack,rx+7,12);
 return true;
}
bool nes_window184_init(struct nes_sink_window184 *s,nes_window184_transfer fn,bool (*guard)(void *),void *ctx,unsigned limit){
 if(!s)return false;
 memset(s,0,sizeof(*s));
 if(!fn||!guard||!limit||limit>65536)return fail(s,1);
 s->transfer=fn;s->guard=guard;s->ctx=ctx;s->poll_limit=limit;
 uint8_t ack[12];if(!status(s,ack))return false;s->initialized=true;return true;
}
static bool valid(struct nes_sink_window184 *s,const uint8_t *p,unsigned n){
 if(!s||!s->initialized||s->error)return false;
 if(!p||n<16||n>256||n!=16u+p[12]+((unsigned)p[13]<<8))return fail(s,1);
 return true;
}
static bool credit(struct nes_sink_window184 *s){
 if((uint16_t)(s->sent-s->retired)<4)return true;
 uint8_t ack[12];
 for(unsigned i=0;i<s->poll_limit;i++){
  if(!status(s,ack))return false;
  if((uint16_t)(s->sent-s->retired)<4)return true;
 }
 return fail(s,7);
}
static bool send(struct nes_sink_window184 *s,const uint8_t *p,unsigned n){
 if(!credit(s))return false;
 uint8_t tx[259],rx[259];tx[0]=0xe1;memcpy(tx+1,p,n);uint16_t c=0xffff;
 for(unsigned i=0;i<=n;i++)c=crc16(c,tx[i]);
 tx[n+1]=(uint8_t)(c>>8);tx[n+2]=(uint8_t)c;
 if(!io(s,tx,rx,n+3))return false;
 s->sent++;s->ever_sent=true;memcpy(s->last,p,10);return true;
}
bool nes_window184_enqueue(void *ctx,const uint8_t *p,unsigned n){
 struct nes_sink_window184 *s=ctx;if(!valid(s,p,n))return false;
 if(p[0]!=2&&p[0]!=4&&p[0]!=5)return fail(s,1);
 return send(s,p,n);
}
bool nes_window184_drain(struct nes_sink_window184 *s,uint8_t ack[12]){
 if(!s||!s->initialized||s->error||!ack)return false;
 for(unsigned i=0;i<s->poll_limit;i++){
  if(!status(s,ack))return false;
  if(s->retired==s->sent){
   if(s->ever_sent&&(ack[0]!=(s->last[0]==3?1:0)||ack[1]!=s->last[0]||memcmp(ack+2,s->last+2,8)||ack[10]!=0x65||ack[11]!=0x9a))return fail(s,8);
   return true;
  }
 }
 return fail(s,7);
}
bool nes_window184_barrier(void *ctx,const uint8_t *p,unsigned n,uint8_t ack[12]){
 struct nes_sink_window184 *s=ctx;if(!valid(s,p,n)||!ack)return false;
 if(p[0]!=1&&p[0]!=3)return fail(s,1);
 if(s->ever_sent && !nes_window184_drain(s,ack))return false;
 return send(s,p,n)&&nes_window184_drain(s,ack);
}
