/* SPDX-License-Identifier: MIT */
#include "nes_native_runtime165.h"
#include <string.h>
static bool fail(struct nes_native_runtime165 *s,unsigned reason){
 if(!s->result)s->result=(uint8_t)reason;
 s->receiver_error=s->receiver?s->receiver->error:0;
 s->video_error=s->video?s->video->error:0;
 return false;
}
static bool guard(void *ctx){
 struct nes_native_runtime165 *s=ctx;
 if(s->result)return false;
 if(s->inside_transfer)return fail(s,NES_RUNTIME165_IO);
 if((uint32_t)(s->ticks(s->ctx)-s->started)>=s->limit)
  return fail(s,NES_RUNTIME165_DEADLINE);
 if(!s->service(s->ctx))return fail(s,NES_RUNTIME165_SERVICE);
 return true;
}
static bool transfer(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 struct nes_native_runtime165 *s=ctx;
 if(!guard(s))return false;
 s->inside_transfer=true;
 bool ok=s->transfer(s->ctx,tx,rx,n);
 s->inside_transfer=false;s->transactions++;s->wire_bytes+=n;
 if(!ok)return fail(s,NES_RUNTIME165_IO);
 return guard(s);
}
bool nes_runtime165_begin(struct nes_native_runtime165 *s,struct nes_native165 *r,
 struct nes_native_video165 *v,const uint16_t palette[64],
 nes_native165_transfer_fn fn,uint32_t (*ticks)(void *),bool (*service)(void *),
 void *ctx,uint32_t limit){
 if(!s)return false;
 memset(s,0,sizeof(*s));
 if(!r||!v||!palette||!fn||!ticks||!service||!limit||limit>=0x80000000u)
  return fail(s,NES_RUNTIME165_ARGUMENT);
 s->receiver=r;s->video=v;s->palette=palette;s->transfer=fn;
 s->ticks=ticks;s->service=service;s->ctx=ctx;s->limit=limit;
 s->started=ticks(ctx);nes_native165_reset(r);memset(v,0,sizeof(*v));
 s->transport=(struct nes_sink_spi165){transfer,s,guard,65536};
 nes_sink165_reset(&s->sink,nes_sink_spi165_exchange,&s->transport);
 return true;
}
bool nes_runtime165_step(struct nes_native_runtime165 *s){
 if(!s||s->result)return false;
 if(!guard(s))return false;
 /* Backstop if the external tick stops; not an elapsed-time estimate. */
 if(s->steps++==4194304u)return fail(s,NES_RUNTIME165_LIMIT);
 struct nes_native165 *r=s->receiver;
 if(r->state==NES_NATIVE165_COMPLETE){
  if(!nes_native165_prepare(r,true,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);
 }else if(r->state!=NES_NATIVE165_COMMITTED){
  if(!nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);
 }
 if(r->state==NES_NATIVE165_COMMITTED){
  if(!guard(s)||!nes_sink165_begin(&s->sink,r->generation)||
     !nes_native_video165_build(r,s->palette,s->video,nes_sink165_pattern,&s->sink)||
     !nes_sink165_seal(&s->sink,s->video,5000)||!guard(s))
   return fail(s,NES_RUNTIME165_DISPLAY);
  if(!s->sink.displayed)return fail(s,NES_RUNTIME165_DISPLAY);
  s->frames++;s->generation=r->generation;
  nes_native165_consumed(r); /* Only after matching SEAL/display ACK. */
 }
 return true;
}
