# SPDX-License-Identifier: MIT
"""Materialize the 746 sender with a guarded E0 retry interval measured on the ARM."""
import argparse
from pathlib import Path

from nes_raw506 import once
from prepare_nes_oam746 import prepare as prepare746


def prepare(base,out,fold=False,debt=False):
    prepare746(base,out)
    def edit(name,old,new):
        target=out/name
        source=target if target.exists() else base/'src'/name
        target.write_text(once(source.read_text(),old,new),encoding='utf8',newline='\n')
    edit('nes_sink_window184.h',' uint32_t serial;',' uint32_t serial,retry_cycles;')
    edit('nes_native_sink165.c','job.source=p->oam;','job.retry_cycles=0;job.source=p->oam;')
    edit('nes_plan_service200.c','''    if(!nes_window184_drain(p->window,ack) ||
       (!(p->window->status_flags&8) &&''','''    /* Scope the deadline to an outstanding map with a checked OBJ
     * waiting behind the previous 48-byte BG. No IRQ grants ownership. */
    struct nes_oam746 *o=p->window->pending_oam;
    if(o && p->bulk_valid && p->bulk[1]==0 && p->bulk[2]==48 && !p->bulk[3] && d[1]==1)
     o->retry_cycles=1;
    bool drained=nes_window184_drain(p->window,ack);
    if(o)o->retry_cycles=0;
    if(!drained || (!(p->window->status_flags&8) &&''')
    edit('nes_sink_window184.c','#include "crc.h"','#include "crc.h"\n#include "nes_cost471.h"')
    edit('nes_sink_window184.c','''  uint16_t before=s->retired;
  if(!status(s,ack))return false;
  if(s->retired==s->sent){''','''  uint16_t before=s->retired;
  struct nes_oam746 *o=s->pending_oam;
  bool timed=o && o->retry_cycles && nes_cost471_available;
  uint32_t start=timed?nes_cost471_now():0;
  if(!status(s,ack))return false;
  if(timed){
   uint32_t elapsed=nes_cost471_now()-start;
   o->retry_cycles=elapsed>21504u?21504u:elapsed?elapsed:1u;
  }
  if(s->retired==s->sent){''')
    if fold or debt:
        edit('nes_sink_window184.c','static bool status(', """/* x^8 = x^2 + x + 1 modulo 0x107. Fold the two overflow
 * coefficients first, then finish the same CRC-8 without a lookup table. */
static uint8_t folded747(const uint8_t *p,unsigned n){
 uint8_t c=0;
 while(n--){
  unsigned x=c^*p++;
  x^=(x>>6)^(x>>7);
  c=(uint8_t)(x^(x<<1)^(x<<2));
 }
 return c;
}
static bool status(""")
        edit('nes_sink_window184.c','uint8_t c=nes_wire723_crc8(rx+1,18);',"""bool final=s->pending_oam && s->pending_oam->retry_cycles &&
            rx[3]==rx[5] && rx[4]==rx[6];
 uint8_t c=final?folded747(rx+1,18):nes_wire723_crc8(rx+1,18);""")
    if debt:
        edit('nes_sink_window184.h',' uint32_t serial,retry_cycles;',' uint32_t serial,retry_cycles;\n bool input_owed;')
        edit('nes_native_sink165.c','job.retry_cycles=0;','job.input_owed=false;job.retry_cycles=0;')
        edit('nes_plan_service200.c',"""    if(o)o->retry_cycles=0;
    if(!drained || (!(p->window->status_flags&8) &&
        !p->window->wait(p->window->ctx,p->window->guard,4,false)))return fail(p,5);""","""    bool prioritize=o && o->retry_cycles;
    if(o)o->retry_cycles=0;
    if(!drained)return fail(p,5);
    if(!(p->window->status_flags&8)){
     if(prioritize){
      if(!p->window->guard(p->window->ctx))return fail(p,5);
      o->input_owed=true;
     }else if(!p->window->wait(p->window->ctx,p->window->guard,4,false))return fail(p,5);
    }""")
        edit('nes_native_sink165.c',""" if(w)w->pending_oam=NULL;
 return ok;""",""" if(w)w->pending_oam=NULL;
 if(ok && job.input_owed){
  uint8_t ack[12];
  if(!nes_window184_drain(w,ack) || !w->wait(w->ctx,w->guard,4,false))return fail(s,5);
 }
 return ok;""")
    decl='bool nes_cost474_pause(void *ctx,bool (*guard)(void *),unsigned reason,bool progress)'
    name='nes_cost471.c'
    edit(name,decl+'{',decl.replace('474_pause','747_pause').replace('bool progress)','bool progress,uint32_t limit)')+'{')
    edit(name,'while(elapsed<84u*128u);','while(elapsed<limit);')
    edit(name,' w->cycles+=elapsed;if(elapsed>w->max_cycles)w->max_cycles=elapsed;\n return true;\n}', ' w->cycles+=elapsed;if(elapsed>w->max_cycles)w->max_cycles=elapsed;\n return true;\n}\n'+decl+'{\n return nes_cost747_pause(ctx,guard,reason,progress,84u*128u);\n}')
    edit('nes_cost471.h','bool nes_cost474_pause(', 'bool nes_cost747_pause(void *,bool (*)(void *),unsigned,bool,uint32_t);\nbool nes_cost474_pause(')
    edit('nes_native_runtime165.c',' return nes_cost474_pause(ctx,check,reason,progress);',''' struct nes_oam746 *o=s->transport.pending_oam;
 unsigned limit=(reason==1 && o && o->retry_cycles)?o->retry_cycles:84u*128u;
 return nes_cost747_pause(ctx,check,reason,progress,limit);''')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','out'):p.add_argument(k,type=Path)
    p.add_argument('--fold',action='store_true')
    p.add_argument('--debt',action='store_true')
    a=p.parse_args();prepare(a.base,a.out,a.fold,a.debt)
