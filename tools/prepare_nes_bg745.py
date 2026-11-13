# SPDX-License-Identifier: MIT
"""Issue verified reusable OAM (and its ready OBJ) after the final map following a three-tile BG."""
import argparse
from pathlib import Path
from prepare_nes_receipt742 import prepare as receipt742
from nes_raw506 import once


def prepare(base,out,*,service=False,input_first=False):
    receipt742(base,out)
    # Keep 727's independent through(BG) and latest-map ACK validation. In
    # particular, a three-tile BG receipt is not a 48-byte VRAM DMA receipt.
    (out/'nes_plan_service200.c').write_bytes((base/'src/nes_plan_service200.c').read_bytes())
    path=out/'nes_native_sink165.c'
    s=path.read_text()
    s=once(s,'s->plan->window->last[1]==2 && (rows', '''s->plan->window->last[1]==2 && !s->obj_next &&
     s->plan->bulk_valid && s->plan->bulk[1]==0 &&
     s->plan->bulk[2]==48 && !s->plan->bulk[3] && (rows''')
    if service:
        s=once(s,'==2 && !s->obj_next &&','==2 &&')
        s=once(s,'unsigned left=w->poll_limit;', 'unsigned left=w->poll_limit;bool reserved=false;')
        s=once(s,'if((w->status_flags&8) || !w->wait)break;', '''if(!w->wait)break;
    if(w->status_flags&8){
     if(!early)break;
     if(!reserved){
      /* Charge one 1536-byte DMA at 8 SNES clocks/byte (84 MHz ARM).
       * Sticky progress is not a second completion. Never extend the
       * existing deadline; every turn still checks E0, credit and STOP. */
      uint32_t limit=nes_cost471_now()-now+48128u;
      if(limit<until)until=limit;
      reserved=true;
     }
    }''')
    path.write_text(s,encoding='utf8',newline='\n')
    if input_first:
        plan=out/'nes_plan_service200.c'
        src=plan.read_text()
        old="""if(!nes_window184_drain(p->window,ack) ||
       (!(p->window->status_flags&8) &&
        !p->window->wait(p->window->ctx,p->window->guard,4,false)))return fail(p,5);"""
        new="""/* The previous tile's checked retirement already completed. Service
     * one real input before sampling the final map identity for this OBJ. */
    bool before=p->bulk_valid && p->bulk[1]==0 && p->bulk[2]==48 && !p->bulk[3] &&
                d[1]==1 && d[2]==32 && d[3]==1;
    if(before && !p->window->wait(p->window->ctx,p->window->guard,4,false))return fail(p,5);
    if(!nes_window184_drain(p->window,ack) ||
       (!before && !(p->window->status_flags&8) &&
        !p->window->wait(p->window->ctx,p->window->guard,4,false)))return fail(p,5);"""
        plan.write_text(once(src,old,new),encoding='utf8',newline='\n')



if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--service',action='store_true')
    p.add_argument('--input-first',action='store_true')
    a=p.parse_args();prepare(a.base,a.out,service=a.service,input_first=a.input_first)
