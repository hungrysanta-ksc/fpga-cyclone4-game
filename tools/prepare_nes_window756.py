# SPDX-License-Identifier: MIT
"""Independent 753 overlays: interleave guarded map offers with OBJ, or send checked deltas."""
import argparse
from pathlib import Path

from nes_raw506 import once, sha
from prepare_nes_group628 import HISTORY


def prepare(src,out,mode):
    assert sha(src/'obj-nes-100/firmware.stm')=='192cf5becb19bb58ede0be25be73d91e4c1fee1f836eadabcb9999ac2af929a6'
    out.mkdir(parents=True,exist_ok=False)
    def edit(name,changes):
        s=(src/name).read_text()
        for before,after in changes:
            s=once(s,before,after)
        (out/name).write_text(s,encoding='utf8',newline='\n')
    refresh=mode=='refresh'
    if refresh:mode='overlap'
    narrow=mode.endswith('page')
    mode=mode.removesuffix('page')
    if mode in ('overlap','both'):
        loop='for(unsigned rank=0;rank<8;rank++)for(unsigned i=0;i<s->counts[2];i++){'
        edit('nes_planner211.c', [(loop,'''for(unsigned rank=0;rank<8;rank++){
  /* Every earlier BG row is immutable. Leave checked bulk and a new
   * head their existing priority, including at a missed queue credit. */
  if(s->counts[2] && resident->offer_map && !resident->offer_map(resident->ctx,2))return fail(p,7);
  for(unsigned i=0;i<s->counts[2];i++){'''),
          (' /* CGRAM becomes',' } /* ranks */\n /* CGRAM becomes')])
        edit('nes_resident211.h',[('(*offer_map)(void *,bool)','(*offer_map)(void *,unsigned)')])
        edit('nes_native_runtime165.c',[('offer527(void *ctx,bool final)','offer527(void *ctx,unsigned final)'),
            (' unsigned mode=final?2:1;', ''' if(final==2 && (s->plan.bank_history!=2 || !s->plan.early ||
     (s->sink.map_next&127)<16 || s->sink.map_next>=64))return true;
 unsigned mode=final?2:1;''')])
        if refresh:
            name='nes_native_runtime165.c'
            target=out/name
            source=target.read_text()
            target.write_text(once(source,' unsigned mode=final?2:1;', ''' if(final==2){
  bool room;
  if(!nes_window532_room(s->plan.window,&room))return false;
  if(!room)return true;
 }
 unsigned mode=final?2:1;'''),encoding='utf8',newline='\n')
    if mode in ('delta','both'):
        history = HISTORY
        capacity = 880
        if narrow:
            capacity = 700
            history = history.replace('i<2048','i<1536').replace('i+4*count<2048','i+4*count<1536').replace('offset+size>4096','offset+size>3584')
        edit('nes_native_sink165.h',[('uint8_t map_next;', f'uint8_t map_next;\n uint8_t history628[2][{capacity}];uint32_t base628[2],epoch628;')])
        edit('nes_native_sink165.c',[
            ('static bool packet_wire', history+'\nstatic bool packet_wire'),
            (' put16(b+12,n);if(n)memcpy(b+16,data,n);',''' if(b[0]==2 && section==2){
  unsigned packed=groups628(s,b+16,at,data,n);
  if(packed){b[0]=9;put16(b+14,n);n=packed;data=NULL;}
 }
 put16(b+12,n);if(n && data)memcpy(b+16,data,n);'''),
            (' uint8_t b[12];put16(b,0x4891);',''' if(s->epoch628!=r->epoch){
  s->base628[0]=s->base628[1]=0;s->epoch628=r->epoch;
 }
 uint8_t b[12];put16(b,0x4891);'''),
            ('s->last_generation=s->generation;', 'publish628(s,p->map+2048);s->last_generation=s->generation;'),
            ('s->error=(uint8_t)e;', 's->base628[0]=s->base628[1]=0;s->error=(uint8_t)e;')])
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('src','out'):p.add_argument(key,type=Path)
    p.add_argument('mode',choices=('refresh','overlap','delta','both','deltapage','bothpage'))
    a=p.parse_args()
    prepare(a.src,a.out,a.mode)
