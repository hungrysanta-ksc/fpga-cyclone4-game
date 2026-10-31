# SPDX-License-Identifier: MIT
"""508 END-before-ordinary scheduling with bounded bulk retirement watermark."""
import argparse,json
from pathlib import Path
from check_nes_game478 import sha
from nes_raw506 import once

def prepare(a):
    a.out.mkdir(parents=True,exist_ok=False);patch=a.out/'patch';patch.mkdir();pins={}
    def get(n):p=a.base/n;pins[n]=sha(p);return p.read_text()
    def put(n,s):(patch/n).write_text(s,encoding='utf8',newline='\n')
    n='nes_plan_service200.h';s=get(n)
    s=once(s,'bool early;','bool early,ending;')
    s=once(s,'uint8_t bulk[12];bool bulk_valid,bulk_pending;','uint8_t bulk[12];bool bulk_valid,bulk_pending;uint16_t bulk_until;')
    s=once(s,'bool nes_plan200_finish(struct nes_plan200 *);','bool nes_plan200_end(struct nes_plan200 *);\nbool nes_plan200_progress(struct nes_plan200 *,bool);')
    put(n,s)
    n='nes_native_sink165.h';s=get(n)
    s=once(s,'struct nes_native_sink165 {','struct nes_plan200;\nstruct nes_native_sink165 {\n struct nes_plan200 *plan;')
    put(n,s)
    n='nes_sink_window184.h';s=get(n)
    s=once(s,'bool nes_window184_drain(struct nes_sink_window184 *,uint8_t ack[12]);','bool nes_window184_drain(struct nes_sink_window184 *,uint8_t ack[12]);\nbool nes_window184_through(struct nes_sink_window184 *,uint8_t ack[12],uint16_t);')
    put(n,s)
    n='nes_sink_window184.c';s=get(n)
    s=once(s,'bool nes_window184_drain(struct nes_sink_window184 *s,uint8_t ack[12]){','bool nes_window184_through(struct nes_sink_window184 *s,uint8_t ack[12],uint16_t target){')
    s=once(s,'if(!s||!s->initialized||s->error||!ack)return false;','if(!s||!s->initialized||s->error||!ack)return false;\n if((uint16_t)(s->sent-target)>4)return fail(s,5);')
    s=once(s,'   return wait474(s,s->last[0]==3?2:1,true);\n  }','  }\n  /* Every retired packet was independently checked by the FPGA.\n   * The full latest identity remains mandatory when the queue is empty. */\n  if((uint16_t)(s->sent-s->retired)<=(uint16_t)(s->sent-target))\n   return wait474(s,s->last[0]==3?2:1,true);')
    s=once(s,'bool nes_window184_barrier(','''bool nes_window184_drain(struct nes_sink_window184 *s,uint8_t ack[12]){
 return s && nes_window184_through(s,ack,s->sent);
}
bool nes_window184_barrier(''')
    put(n,s)
    n='nes_plan_service200.c';s=get(n)
    s=once(s,'p->finished||p->sink->state','p->sink->state')
    s=once(s,"!p->window||p->window->last[0]!=7||!nes_window184_drain(p->window,ack)","!p->window||!nes_window184_through(p->window,ack,p->bulk_until)")
    s=once(s,'memcpy(p->bulk,d,12);p->bulk_valid=p->bulk_pending=true;','memcpy(p->bulk,d,12);p->bulk_valid=p->bulk_pending=true;p->bulk_until=p->window->sent;')
    s=once(s,'    *flags=0;return true;','    *flags=4;return true;')
    s=once(s,'  *flags=0;\n }else{','  *flags=4;\n }else{')
    s=once(s,'if(q->kind>2||q->generation!=p->sink->generation)','if(p->ending||q->kind>2||q->generation!=p->sink->generation)')
    s=once(s,'bool nes_plan200_finish(struct nes_plan200 *p){','bool nes_plan200_end(struct nes_plan200 *p){')
    s=once(s,'if(!p->started)return fail(p,1);','if(!p->started||p->ending)return fail(p,1);')
    s=once(s,' if(!append(p,&end)||!flush(p))return false;\n uint8_t flags;',''' if(!append(p,&end)||!flush(p))return false;
 p->ending=true;return true;
}
bool nes_plan200_progress(struct nes_plan200 *p,bool finish){
 if(!p||!p->ending)return false;
 if(p->finished)return valid(p);
 uint8_t flags;''')
    s=once(s,'  if(flags&2){p->finished=true;return true;}','''  if(flags&2){p->finished=true;return true;}
  /* Drain ready bulk before ordinary. An empty producer waiting for ROM
   * yields one ordinary packet; no SPI callback or payload pointer is retained. */
  if(!finish && !(flags&4))return complete485(p);''')
    s=once(s,'p->early=false;p->bulk_valid=p->bulk_pending=false;','p->early=p->ending=false;p->bulk_valid=p->bulk_pending=false;')
    put(n,s)
    n='nes_native_sink165.c';s=get(n)
    s=once(s,'#include "nes_sink_trace168.h"','#include "nes_sink_trace168.h"\n#include "nes_plan_service200.h"')
    s=once(s,' bool bulk_submit=op==23;if(bulk_submit)op=7;',''' // Service BEFORE capturing sequence/state or arming BUSY: a bulk packet
 // can be submitted here and owns its own sequence. Bulk itself never recurses.
 if(s->plan && op>=2 && op!=7 && op!=23 &&
    !nes_plan200_progress(s->plan,op==3))return fail(s,5);
 bool bulk_submit=op==23;if(bulk_submit)op=7;''')
    put(n,s)
    n='nes_native_runtime165.c';s=get(n)
    s=once(s,'s->sink.enqueue=nes_window184_enqueue;','s->sink.enqueue=nes_window184_enqueue;s->sink.plan=&s->plan;')
    s=once(s,'nes_plan200_finish(&s->plan)','nes_plan200_end(&s->plan)')
    put(n,s)
    r=dict(scope=__doc__,base=pins,patch={p.name:sha(p)for p in patch.iterdir()},new_global_objects=0,added_sink_pointer_B=4,new_FPGA=False,new_SNES=False,delivery=False)
    (a.out/'prepare.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['base','out']:p.add_argument('--'+n,type=Path,required=True)
    prepare(p.parse_args())
